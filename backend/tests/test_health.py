import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_root_endpoint():
    """Kiểm tra endpoint gốc GET / trả về thông tin hệ thống và status 200."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "project" in data
        assert "version" in data


@pytest.mark.asyncio
async def test_api_v1_info_endpoint():
    """Kiểm tra endpoint GET /api/v1/info hoạt động."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/info")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "v1"
