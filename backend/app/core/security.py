import hashlib
import hmac
import json
import base64
import time
import uuid
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Dict
from fastapi import Header, HTTPException, Depends, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

# HTTP Bearer scheme
security_bearer = HTTPBearer(auto_error=False)


def is_valid_internal_secret(secret: Optional[str]) -> bool:
    """Kiểm tra tính hợp lệ của X-Internal-Secret theo hằng số thời gian an toàn."""
    if not secret:
        return False
    return secrets.compare_digest(
        secret.encode("utf-8"),
        settings.INTERNAL_API_SECRET.encode("utf-8"),
    )


from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError

# Password Hasher theo khuyến nghị OWASP 2024:
# Argon2id với time_cost=2, memory_cost=65536 (64 MiB), parallelism=2, hash_len=32, salt_len=16
password_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=2,
    hash_len=32,
    salt_len=16,
)


def get_password_hash(password: str) -> str:
    """
    Hash password bằng Argon2id (tiêu chuẩn OWASP hiện hành).
    Tự động sinh salt ngẫu nhiên an toàn trước GPU/ASIC brute-force.
    """
    return password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Xác minh mật khẩu so với hash đã lưu.
    Hỗ trợ đồng thời Argon2id hiện tại và tương thích ngược với PBKDF2-HMAC-SHA256 cũ.
    """
    if not hashed_password or not plain_password:
        return False

    # 1. Thử xác minh bằng Argon2id (bắt đầu bằng $argon2id$ hoặc $argon2)
    if hashed_password.startswith("$argon2"):
        try:
            return password_hasher.verify(hashed_password, plain_password)
        except (VerifyMismatchError, InvalidHashError):
            return False
        except Exception:
            return False

    # 2. Hỗ trợ tương thích ngược (Backward Compatibility) cho PBKDF2 cũ
    if hashed_password.startswith("pbkdf2_sha256$"):
        try:
            parts = hashed_password.split("$")
            if len(parts) != 4:
                return False
            iterations = int(parts[1])
            salt = parts[2]
            expected_key = parts[3]

            calculated_key = hashlib.pbkdf2_hmac(
                "sha256",
                plain_password.encode("utf-8"),
                salt.encode("utf-8"),
                iterations,
            ).hex()

            return secrets.compare_digest(calculated_key, expected_key)
        except Exception:
            return False

    return False


def needs_password_rehash(hashed_password: str) -> bool:
    """
    Kiểm tra xem mật khẩu đã băm có cần được nâng cấp (rehash) lên chuẩn Argon2id mới nhất không.
    Trả về True nếu hash là định dạng cũ (PBKDF2) hoặc thông số Argon2 chưa tối ưu.
    """
    if not hashed_password:
        return True
    if not hashed_password.startswith("$argon2"):
        return True
    try:
        return password_hasher.check_needs_rehash(hashed_password)
    except Exception:
        return True



import jwt


def hash_token(token: str) -> str:
    """Tính SHA-256 hash của chuỗi token thô để lưu an toàn vào DB."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
    jti: Optional[str] = None,
) -> str:
    """
    Tạo Access Token xác thực chuẩn JWT (HS256) ngắn hạn (mặc định 30 phút).
    Bắt buộc có các claims: sub, exp, iat, type, jti.
    """
    to_encode = data.copy()
    if "sub" not in to_encode or not to_encode["sub"]:
        raise ValueError("Missing 'sub' claim for access token creation.")

    sub_str = str(to_encode["sub"])
    try:
        uuid.UUID(sub_str)
    except (ValueError, TypeError, AttributeError):
        raise ValueError(f"Invalid UUID for 'sub' claim: {sub_str}")

    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    token_jti = str(jti or to_encode.get("jti") or uuid.uuid4())

    to_encode.update({
        "sub": sub_str,
        "type": "access",
        "jti": token_jti,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    })

    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
    jti: Optional[str] = None,
    family_id: Optional[str] = None,
) -> str:
    """
    Tạo Refresh Token chuẩn JWT (HS256) dài hạn (mặc định 30 ngày) phục vụ rotation.
    Bắt buộc có các claims: sub, exp, iat, type, jti. Có thể kèm family_id.
    """
    to_encode = data.copy()
    if "sub" not in to_encode or not to_encode["sub"]:
        raise ValueError("Missing 'sub' claim for refresh token creation.")

    sub_str = str(to_encode["sub"])
    try:
        uuid.UUID(sub_str)
    except (ValueError, TypeError, AttributeError):
        raise ValueError(f"Invalid UUID for 'sub' claim: {sub_str}")

    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))
    token_jti = str(jti or to_encode.get("jti") or uuid.uuid4())

    payload = {
        "sub": sub_str,
        "type": "refresh",
        "jti": token_jti,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if family_id or "family_id" in to_encode:
        payload["family_id"] = str(family_id or to_encode["family_id"])
    if "email" in to_encode:
        payload["email"] = str(to_encode["email"])

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(
    token: str,
    expected_type: Optional[str] = "access",
    require_claims: Optional[list] = None,
) -> Dict[str, Any]:
    """
    Giải mã và xác thực chặt chẽ chữ ký JWT bằng PyJWT với whitelist algorithm từ config.
    Kiểm tra claims bắt buộc: exp, iat, sub, type, jti.
    Xác minh sub là UUID hợp lệ.
    """
    req_claims = require_claims or ["exp", "iat", "sub", "type", "jti"]

    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={
            "require": req_claims,
            "verify_exp": True,
            "verify_iat": True,
            "verify_signature": True,
        },
    )

    sub_str = str(payload.get("sub", ""))
    try:
        uuid.UUID(sub_str)
    except (ValueError, TypeError, AttributeError):
        raise jwt.InvalidTokenError("Token subject (sub) is not a valid UUID")

    if expected_type is not None:
        token_type = payload.get("type")
        if token_type != expected_type:
            raise jwt.InvalidTokenError(f"Invalid token type: expected '{expected_type}', got '{token_type}'")

    return payload


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Giải mã và xác thực chữ ký access token. Trả về None nếu token lỗi hoặc hết hạn.
    Duy trì tương thích với các điểm gọi cũ.
    """
    try:
        return decode_token(token, expected_type="access")
    except Exception:
        return None


def decode_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Giải mã và xác thực chữ ký refresh token. Trả về None nếu token lỗi hoặc hết hạn.
    """
    try:
        return decode_token(token, expected_type="refresh")
    except Exception:
        return None


async def verify_internal_secret(
    x_internal_secret: Optional[str] = Header(None, alias="X-Internal-Secret")
) -> bool:
    """
    FastAPI Dependency: Bảo vệ các API endpoints nội bộ (Discord Bot adapter, background scripts).
    """
    if not x_internal_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing 'X-Internal-Secret' header",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not is_valid_internal_secret(x_internal_secret):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal API secret",
        )

    return True


async def get_current_user_optional(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    x_internal_secret: Optional[str] = Header(None, alias="X-Internal-Secret"),
    token: Optional[str] = Query(None, description="JWT Token qua query param cho trình duyệt xem inline iframe hoặc tải file"),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Dependency lấy User hiện tại nếu có Bearer token, Query token, hoặc Internal Secret (fallback user).
    """
    # 1. Thử lấy từ Bearer Token hoặc Query token
    raw_token = auth.credentials if (auth and auth.credentials) else token
    if raw_token:
        try:
            payload = decode_token(raw_token, expected_type="access")
            user_id = uuid.UUID(str(payload["sub"]))
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            if user and user.is_active:
                return user
        except Exception:
            pass

    # 2. Thử fallback nếu có X-Internal-Secret hợp lệ
    if is_valid_internal_secret(x_internal_secret):
        stmt = select(User).order_by(User.created_at.asc()).limit(1)
        result = await db.execute(stmt)
        default_user = result.scalar_one_or_none()
        if not default_user:
            default_user = User(
                id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
                email="system@jobhunter.internal",
                hashed_password="internal_system_service",
                full_name="Internal System Service",
                is_active=True,
                is_superuser=True,
            )
        return default_user

    return None


async def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency bắt buộc người dùng đã đăng nhập hợp lệ.
    Bắt chi tiết ExpiredSignatureError và InvalidTokenError để trả thông báo chuẩn RFC 6750.
    """
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required. Missing Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(auth.credentials, expected_type="access")
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token", error_description="The access token has expired"'},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = uuid.UUID(str(payload["sub"]))
    try:
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account not found or deactivated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )



async def get_authenticated_user_or_internal(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    x_internal_secret: Optional[str] = Header(None, alias="X-Internal-Secret"),
    token: Optional[str] = Query(None, description="JWT Token qua query param cho trình duyệt xem inline iframe hoặc tải file"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency bắt buộc: yêu cầu Bearer Token người dùng hợp lệ
    HOẶC Query Token hợp lệ (cho iframe/download)
    HOẶC X-Internal-Secret hợp lệ từ internal services (Discord bot / Workers).
    """
    user = await get_current_user_optional(auth=auth, x_internal_secret=x_internal_secret, token=token, db=db)
    if not user:
        if x_internal_secret and not is_valid_internal_secret(x_internal_secret):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid internal API secret.",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a valid Bearer token, query token or 'X-Internal-Secret'.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def verify_admin_access(
    x_internal_secret: Optional[str] = Header(None, alias="X-Internal-Secret"),
    user: Optional[User] = Depends(get_current_user_optional),
) -> bool:
    """
    Xác thực quyền quản trị hệ thống: yêu cầu X-Internal-Secret hợp lệ hoặc tài khoản Superuser.
    """
    if x_internal_secret:
        if is_valid_internal_secret(x_internal_secret):
            return True
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal API secret for system administrative operations",
        )

    if user and getattr(user, "is_superuser", False):
        return True

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Administrative privilege required for this system operation.",
    )


async def verify_profile_access(
    x_internal_secret: Optional[str] = Header(None, alias="X-Internal-Secret"),
    user: Optional[User] = Depends(get_current_user_optional),
) -> bool:
    """
    Cho phép truy cập profile từ Web App (đã đăng nhập) hoặc Discord Bot có X-Internal-Secret hợp lệ.
    """
    if x_internal_secret:
        if is_valid_internal_secret(x_internal_secret):
            return True
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal API secret",
        )

    if user:
        return True

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required to access candidate profile.",
        headers={"WWW-Authenticate": "Bearer"},
    )

