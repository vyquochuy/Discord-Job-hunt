import logging
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app

logger = logging.getLogger("test.health")


@pytest.mark.asyncio
async def test_root_endpoint():
    """Kiểm tra root endpoint (GET /) và health check (GET /health)."""
    logger.info("=== [TEST] Root and Health Endpoints ===")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. GET /
        res_root = await client.get("/")
        logger.info(f"  GET / Response Status: {res_root.status_code}, Body: {res_root.json()}")
        assert res_root.status_code == 200
        root_data = res_root.json()
        assert root_data["project"] == "AI Job Hunter Agent API"
        assert "environment" in root_data

        # 2. GET /health (Trả về 200 nếu kết nối đủ DB/Redis, hoặc 503 degraded khi chạy unit test độc lập)
        res_health = await client.get("/health")
        logger.info(f"  GET /health Response Status: {res_health.status_code}, Body: {res_health.json()}")
        assert res_health.status_code in [200, 503]
        health_data = res_health.json()
        assert health_data["status"] in ["ok", "degraded"]
        assert "components" in health_data


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
