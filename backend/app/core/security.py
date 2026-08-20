from typing import Optional
import secrets
from fastapi import Header, HTTPException, status

from app.core.config import settings


async def verify_internal_secret(
    x_internal_secret: Optional[str] = Header(None, alias="X-Internal-Secret")
) -> bool:
    """
    FastAPI Dependency: Bảo vệ các API endpoints nội bộ.
    Chỉ cho phép Discord Bot hoặc các client có đúng X-Internal-Secret truy cập.
    """
    # Nếu đang ở môi trường development và chưa đổi secret mặc định, vẫn cho phép nếu khớp
    if not x_internal_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing 'X-Internal-Secret' header",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Sử dụng secrets.compare_digest để chống tấn công so khớp thời gian (timing attack)
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
