import pytest
from starlette.requests import Request
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.limiter import limiter, get_client_ip


def test_get_client_ip_direct_connection():
    """Kiểm tra get_client_ip khi không có header proxy, fallback về client host."""
    scope = {
        "type": "http",
        "client": ("192.168.1.50", 12345),
        "headers": [],
    }
    request = Request(scope)
    assert get_client_ip(request) == "192.168.1.50"


def test_get_client_ip_x_forwarded_for():
    """Kiểm tra get_client_ip khi đi qua Reverse Proxy (Render / Nginx / ALB)."""
    scope = {
        "type": "http",
        "client": ("10.0.0.1", 12345),
        "headers": [
            (b"x-forwarded-for", b"203.0.113.195, 70.41.3.18, 150.172.238.178"),
        ],
    }
    request = Request(scope)
    # Phải lấy IP đầu tiên của chuỗi (IP gốc của client)
    assert get_client_ip(request) == "203.0.113.195"


def test_get_client_ip_cf_connecting_ip():
    """Kiểm tra get_client_ip khi đi qua Cloudflare Pages/CDN."""
    scope = {
        "type": "http",
        "client": ("172.70.1.1", 12345),
        "headers": [
            (b"cf-connecting-ip", b"198.51.100.42"),
        ],
    }
    request = Request(scope)
    assert get_client_ip(request) == "198.51.100.42"


def test_rate_limiting_enforcement_and_isolation():
    """Kiểm tra rate limit kích hoạt 429 và phân lập hạn mức giữa các client IP khác nhau."""
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.get("/test-limit")
    @limiter.limit("2/minute")
    def limited_route(request: Request):
        return {"status": "ok"}

    # Bật limiter trong bài test này
    limiter.enabled = True
    try:
        client = TestClient(app)

        # Client A gửi 2 request hợp lệ
        headers_a = {"X-Forwarded-For": "1.1.1.1"}
        r1 = client.get("/test-limit", headers=headers_a)
        assert r1.status_code == 200

        r2 = client.get("/test-limit", headers=headers_a)
        assert r2.status_code == 200

        # Request thứ 3 của Client A vượt ngưỡng 2/minute -> 429 Too Many Requests
        r3 = client.get("/test-limit", headers=headers_a)
        assert r3.status_code == 429
        assert "Rate limit exceeded" in r3.text

        # Client B (IP khác) vẫn gửi request thành công vì có bucket riêng biệt
        headers_b = {"X-Forwarded-For": "2.2.2.2"}
        r_b = client.get("/test-limit", headers=headers_b)
        assert r_b.status_code == 200

        # Client C qua Cloudflare (CF-Connecting-IP) cũng có bucket riêng biệt
        headers_c = {"CF-Connecting-IP": "3.3.3.3"}
        r_c = client.get("/test-limit", headers=headers_c)
        assert r_c.status_code == 200

    finally:
        # Khôi phục trạng thái
        limiter.enabled = False
