import logging
from unittest.mock import patch
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app

logger = logging.getLogger("test.health")


@pytest.mark.asyncio
async def test_root_endpoint():
    """Kiểm tra root endpoint (GET /) và lightweight liveness health check (GET /health)."""
    logger.info("=== [TEST] Root and Health Liveness Endpoints ===")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. GET / với Accept: application/json
        res_root = await client.get("/", headers={"Accept": "application/json"})
        logger.info(f"  GET / Response Status: {res_root.status_code}, Body: {res_root.json()}")
        assert res_root.status_code == 200
        root_data = res_root.json()
        assert root_data["project"] == "AI Job Hunter Agent API"
        assert "environment" in root_data
        assert root_data["health"] == "/health"
        assert root_data["ready"] == "/health/ready"

        # 2. GET /health (Lightweight liveness probe - 200 OK, KHÔNG truy vấn Database)
        res_health = await client.get("/health")
        logger.info(f"  GET /health Response Status: {res_health.status_code}, Body: {res_health.json()}")
        assert res_health.status_code == 200
        health_data = res_health.json()
        assert health_data["status"] == "ok"
        assert health_data["service"] == "job-hunt-backend"

        # 3. HEAD /health (Kiểm tra liveness phương thức HEAD cho Render/load balancers)
        res_health_head = await client.head("/health")
        assert res_health_head.status_code == 200
        assert res_health_head.text == ""


@pytest.mark.asyncio
async def test_readiness_probe_healthy():
    """Kiểm tra /health/ready khi Database kết nối thành công (HTTP 200)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("app.main.check_db_health", return_value=True):
            res_ready = await client.get("/health/ready")
            assert res_ready.status_code == 200
            data = res_ready.json()
            assert data["status"] == "ready"
            assert data["database"] == "ok"

            res_ready_head = await client.head("/health/ready")
            assert res_ready_head.status_code == 200


@pytest.mark.asyncio
async def test_readiness_probe_unhealthy_no_leak():
    """Kiểm tra /health/ready khi Database mất kết nối (HTTP 503) và đảm bảo không rò rỉ secrets."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("app.main.check_db_health", return_value=False):
            res_ready = await client.get("/health/ready")
            assert res_ready.status_code == 503
            data = res_ready.json()
            assert data["status"] == "not_ready"
            assert data["database"] == "unavailable"

            # Đảm bảo không lộ thông tin nhạy cảm (mật khẩu, chuỗi kết nối, stack traces)
            raw_text = res_ready.text.lower()
            assert "password" not in raw_text
            assert "postgres" not in raw_text
            assert "traceback" not in raw_text
            assert "secret" not in raw_text

            res_ready_head = await client.head("/health/ready")
            assert res_ready_head.status_code == 503


@pytest.mark.asyncio
async def test_api_v1_info_endpoint():
    """Kiểm tra thông tin API v1 (GET /api/v1/info)."""
    logger.info("=== [TEST] API v1 Info Endpoint (GET /api/v1/info) ===")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/info")
        logger.info(f"  GET /api/v1/info Response Status: {response.status_code}, Body: {response.json()}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"
        assert data["version"] == "v1"

