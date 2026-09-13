from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request
from app.core.config import settings


def get_client_ip(request: Request) -> str:
    """
    Lấy IP thực của client. Hỗ trợ reverse proxy ở Production (Cloudflare, Render)
    và fallback về remote address ở Development.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()
    return get_remote_address(request)


# Cấu hình Limiter độc lập theo từng môi trường
if settings.ENVIRONMENT == "production":
    # Production: Sử dụng Redis storage nếu có cấu hình cloud URL (khác localhost),
    # đồng thời nhận diện IP chuẩn qua reverse proxy
    redis_storage = settings.REDIS_URL if settings.REDIS_URL and "127.0.0.1" not in settings.REDIS_URL else None
    limiter = Limiter(
        key_func=get_client_ip,
        storage_uri=redis_storage,
    )
else:
    # Development: Sử dụng in-memory storage (storage_uri=None) để dev cục bộ
    # luôn chạy mượt mà mà không bắt buộc phải bật Redis service
    limiter = Limiter(
        key_func=get_client_ip,
        storage_uri=None,
    )
