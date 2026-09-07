import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import jwt
from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User

logger = logging.getLogger(__name__)


class AuthService:
    """
    Dịch vụ quản lý xác thực phiên, cấp phát và xoay vòng Refresh Token (RTR)
    với cơ chế Token Family Revocation và Atomic Row-Level Locking.
    """

    @staticmethod
    async def issue_token_pair(
        db: AsyncSession,
        user: User,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        family_id: Optional[uuid.UUID] = None,
    ) -> Tuple[str, str]:
        """
        Cấp phát một cặp token mới (Access Token 30m + Refresh Token 30d).
        Lưu bản ghi hash SHA-256 vào database.
        """
        active_family_id = family_id or uuid.uuid4()
        jti_refresh = uuid.uuid4()

        access_token = create_access_token({"sub": str(user.id), "email": user.email})
        refresh_token = create_refresh_token(
            {"sub": str(user.id), "email": user.email},
            jti=str(jti_refresh),
            family_id=str(active_family_id),
        )

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        rt_record = RefreshToken(
            id=uuid.uuid4(),
            user_id=user.id,
            family_id=active_family_id,
            jti=jti_refresh,
            token_hash=hash_token(refresh_token),
            expires_at=expires_at,
            created_at=now,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        db.add(rt_record)
        await db.flush()

        return access_token, refresh_token

    @staticmethod
    async def rotate_refresh_token(
        db: AsyncSession,
        raw_refresh_token: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Thực hiện xoay vòng Refresh Token (Refresh Token Rotation - RTR) nguyên tử:
        1. Decode và kiểm tra chữ ký HS256 + claims bắt buộc.
        2. Khóa dòng database bằng `with_for_update()` để ngăn chặn race conditions.
        3. Nếu token đã thu hồi nhưng nằm trong Grace Period (<= 15s): Trả lại token thay thế đã cấp (không rẽ nhánh).
        4. Nếu token đã thu hồi ngoài Grace Period: Phát hiện REUSE ATTACK -> Thu hồi toàn bộ Token Family của phiên đó.
        5. Nếu token hợp lệ: Đánh dấu revoked_at, liên kết replaced_by_jti, cấp token mới cùng family_id.
        """
        try:
            payload = decode_token(raw_refresh_token, expected_type="refresh")
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired. Please log in again.",
                headers={"WWW-Authenticate": 'Bearer error="invalid_token", error_description="The refresh token has expired"'},
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid refresh token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

        jti_raw = payload.get("jti")
        sub_raw = payload.get("sub")
        if not jti_raw or not sub_raw:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Malformed refresh token claims.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        jti = uuid.UUID(str(jti_raw))
        user_id = uuid.UUID(str(sub_raw))
        provided_hash = hash_token(raw_refresh_token)

        # Invariant 2: Atomic Row-Level Locking (with_for_update)
        stmt = (
            select(RefreshToken)
            .where(RefreshToken.jti == jti)
            .with_for_update()
        )
        result = await db.execute(stmt)
        stored_token = result.scalar_one_or_none()

        if not stored_token or stored_token.token_hash != provided_hash or stored_token.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or unrecognized refresh token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Kiểm tra người dùng
        user_stmt = select(User).where(User.id == user_id)
        user = (await db.execute(user_stmt)).scalar_one_or_none()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account not found or deactivated.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        now = datetime.now(timezone.utc)

        # Xử lý trường hợp Token đã bị thu hồi trước đó
        if stored_token.revoked_at is not None:
            # Đảm bảo múi giờ UTC đồng nhất khi tính toán
            revoked_at_utc = stored_token.revoked_at
            if revoked_at_utc.tzinfo is None:
                revoked_at_utc = revoked_at_utc.replace(tzinfo=timezone.utc)

            elapsed_seconds = (now - revoked_at_utc).total_seconds()

            # Invariant 3: Grace Period Idempotency
            if (
                elapsed_seconds <= settings.ROTATION_GRACE_PERIOD_SECONDS
                and stored_token.replaced_by_jti
            ):
                # Tìm bản ghi token thay thế đã phát hành trước đó
                rep_stmt = (
                    select(RefreshToken)
                    .where(RefreshToken.jti == stored_token.replaced_by_jti)
                    .with_for_update()
                )
                replacement = (await db.execute(rep_stmt)).scalar_one_or_none()
                if replacement and replacement.revoked_at is None:
                    logger.info(
                        f"Grace-period refresh request handled idempotently for user {user_id}, token {jti}."
                    )
                    # Cấp access token mới và trả lại thông tin refresh token hợp lệ đã cấp
                    new_access = create_access_token({"sub": str(user.id), "email": user.email})
                    rep_exp_utc = replacement.expires_at
                    if rep_exp_utc.tzinfo is None:
                        rep_exp_utc = rep_exp_utc.replace(tzinfo=timezone.utc)

                    rem_exp = rep_exp_utc - now
                    if rem_exp.total_seconds() > 0:
                        reconstructed_refresh = create_refresh_token(
                            {"sub": str(user.id), "email": user.email},
                            expires_delta=rem_exp,
                            jti=str(replacement.jti),
                            family_id=str(replacement.family_id),
                        )
                        return new_access, reconstructed_refresh


            # Vượt quá Grace Period hoặc không có replacement -> REUSE ATTACK DETECTED!
            await db.execute(
                update(RefreshToken)
                .where(
                    RefreshToken.family_id == stored_token.family_id,
                    RefreshToken.revoked_at.is_(None),
                )
                .values(revoked_at=now)
            )
            await db.commit()

            logger.warning(
                f"SECURITY ALERT: Refresh token reuse detected for user {user_id}, family {stored_token.family_id}! Entire family revoked."
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Security violation: Revoked refresh token reuse detected. Session terminated.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Kiểm tra token đã hết hạn
        exp_at_utc = stored_token.expires_at
        if exp_at_utc.tzinfo is None:
            exp_at_utc = exp_at_utc.replace(tzinfo=timezone.utc)

        if exp_at_utc < now:
            stored_token.revoked_at = now
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Xoay vòng bình thường (Normal Rotation)
        new_jti = uuid.uuid4()
        stored_token.revoked_at = now
        stored_token.replaced_by_jti = new_jti
        stored_token.last_used_at = now

        new_access = create_access_token({"sub": str(user.id), "email": user.email})
        new_refresh = create_refresh_token(
            {"sub": str(user.id), "email": user.email},
            jti=str(new_jti),
            family_id=str(stored_token.family_id),
        )

        new_rt = RefreshToken(
            id=uuid.uuid4(),
            user_id=user.id,
            family_id=stored_token.family_id,
            jti=new_jti,
            token_hash=hash_token(new_refresh),
            expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            created_at=now,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        db.add(new_rt)
        await db.commit()

        return new_access, new_refresh

    @staticmethod
    async def revoke_refresh_token(
        db: AsyncSession,
        raw_refresh_token: str,
        user_id: Optional[uuid.UUID] = None,
    ) -> bool:
        """
        Thu hồi một Refresh Token cụ thể (ví dụ khi user ấn Logout).
        """
        try:
            payload = decode_token(raw_refresh_token, expected_type="refresh")
            jti = uuid.UUID(str(payload["jti"]))
        except Exception:
            return False

        stmt = select(RefreshToken).where(RefreshToken.jti == jti).with_for_update()
        result = await db.execute(stmt)
        token_record = result.scalar_one_or_none()
        if not token_record:
            return False

        if user_id and token_record.user_id != user_id:
            return False

        now = datetime.now(timezone.utc)
        token_record.revoked_at = now
        await db.commit()
        return True
