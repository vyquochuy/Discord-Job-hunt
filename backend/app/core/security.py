import hashlib
import hmac
import json
import base64
import time
import uuid
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Dict
from fastapi import Header, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db

# HTTP Bearer scheme
security_bearer = HTTPBearer(auto_error=False)


def get_password_hash(password: str) -> str:
    """
    Hash password bằng PBKDF2-HMAC-SHA256 với salt ngẫu nhiên 16 bytes.
    Không phụ thuộc vào binary compiled bên ngoài, tương thích đa nền tảng.
    """
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    )
    return f"pbkdf2_sha256$100000${salt}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Xác minh mật khẩu so với hash đã lưu.
    """
    try:
        parts = hashed_password.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
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


def _b64encode_str(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode("utf-8")).decode("utf-8").rstrip("=")


def _b64decode_str(s: str) -> str:
    padding = 4 - (len(s) % 4)
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s.encode("utf-8")).decode("utf-8")


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Tạo Token xác thực linh hoạt (HMAC-SHA256 Signed Payload).
    Không gò bó kiến trúc JWT cứng nhắc, tự do mở rộng payload.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": int(expire.timestamp()), "iat": int(now.timestamp())})
    
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64encode_str(json.dumps(header, separators=(",", ":")))
    payload_b64 = _b64encode_str(json.dumps(to_encode, separators=(",", ":")))
    
    signing_input = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        settings.JWT_SECRET_KEY.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256
    ).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
    
    return f"{signing_input}.{signature_b64}"


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Giải mã và xác thực chữ ký token.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        
        header_b64, payload_b64, signature_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}"
        
        expected_sig = hmac.new(
            settings.JWT_SECRET_KEY.encode("utf-8"),
            signing_input.encode("utf-8"),
            hashlib.sha256
        ).digest()
        expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode("utf-8").rstrip("=")
        
        if not secrets.compare_digest(signature_b64, expected_sig_b64):
            return None
        
        payload = json.loads(_b64decode_str(payload_b64))
        exp = payload.get("exp")
        if exp and exp < time.time():
            return None
            
        return payload
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

    is_valid = secrets.compare_digest(
        x_internal_secret.encode("utf-8"),
        settings.INTERNAL_API_SECRET.encode("utf-8")
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal API secret",
        )

    return True


async def get_current_user_optional(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    x_internal_secret: Optional[str] = Header(None, alias="X-Internal-Secret"),
    db: AsyncSession = Depends(get_db),
) -> Optional[Any]:
    """
    Dependency lấy User hiện tại nếu có Bearer token hoặc Internal Secret (fallback user).
    """
    from app.models.user import User

    # 1. Thử lấy từ Bearer Token
    if auth and auth.credentials:
        payload = decode_access_token(auth.credentials)
        if payload and "sub" in payload:
            user_id = payload["sub"]
            try:
                stmt = select(User).where(User.id == uuid.UUID(str(user_id)))
                result = await db.execute(stmt)
                user = result.scalar_one_or_none()
                if user and user.is_active:
                    return user
            except Exception:
                pass

    # 2. Thử fallback nếu có X-Internal-Secret hợp lệ
    if x_internal_secret and secrets.compare_digest(
        x_internal_secret.encode("utf-8"),
        settings.INTERNAL_API_SECRET.encode("utf-8")
    ):
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
) -> Any:
    """
    Dependency bắt buộc người dùng đã đăng nhập hợp lệ.
    """
    from app.models.user import User

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not auth or not auth.credentials:
        raise credentials_exception
        
    payload = decode_access_token(auth.credentials)
    if not payload or "sub" not in payload:
        raise credentials_exception
        
    user_id = payload["sub"]
    try:
        stmt = select(User).where(User.id == uuid.UUID(str(user_id)))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise credentials_exception
        return user
    except HTTPException:
        raise
    except Exception:
        raise credentials_exception


async def get_authenticated_user_or_internal(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    x_internal_secret: Optional[str] = Header(None, alias="X-Internal-Secret"),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Dependency bắt buộc: yêu cầu Bearer Token người dùng hợp lệ
    HOẶC X-Internal-Secret hợp lệ từ internal services (Discord bot / Workers).
    """
    user = await get_current_user_optional(auth=auth, x_internal_secret=x_internal_secret, db=db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a valid Bearer token or 'X-Internal-Secret'.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

