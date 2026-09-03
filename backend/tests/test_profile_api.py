import logging
from pathlib import Path
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app

logger = logging.getLogger("test.profile_api")


@pytest_asyncio.fixture
async def test_client():
    """Tạo TestClient với database SQLite in-memory được ghi đè dependency get_db."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_profile_api_authentication(test_client: AsyncClient):
    """Kiểm tra lớp bảo mật Web và X-Internal-Secret: từ chối unauthenticated (401) và secret sai (403)."""
    logger.info("=== [TEST] Profile API Authentication & Security Gate ===")
    
    # 1. Request không xác thực -> 401 Unauthorized
    res_no_auth = await test_client.get("/api/v1/profile")
    logger.info(f"  Unauthenticated Request Status = {res_no_auth.status_code}")
    assert res_no_auth.status_code == 401

    # 2. Sai secret key -> 403 Forbidden
    res_wrong_auth = await test_client.get(
        "/api/v1/profile", headers={"X-Internal-Secret": "wrong_secret_key"}
    )
    logger.info(f"  Wrong Secret Request: Status = {res_wrong_auth.status_code}, Detail = {res_wrong_auth.json()['detail']}")
    assert res_wrong_auth.status_code == 403
    assert "Invalid internal API secret" in res_wrong_auth.json()["detail"]

    # 3. Hợp lệ với X-Internal-Secret -> 200 OK
    res_valid_auth = await test_client.get(
        "/api/v1/profile", headers={"X-Internal-Secret": settings.INTERNAL_API_SECRET}
    )
    assert res_valid_auth.status_code == 200


@pytest.mark.asyncio
async def test_profile_sync_endpoint(test_client: AsyncClient):
    """Kiểm tra endpoint POST /api/v1/profile/sync đồng bộ thành công dữ liệu."""
    logger.info("=== [TEST] Profile Sync Endpoint (POST /api/v1/profile/sync) ===")
    headers = {"X-Internal-Secret": settings.INTERNAL_API_SECRET}

    res = await test_client.post("/api/v1/profile/sync", headers=headers)
    logger.info(f"  Sync Response Status = {res.status_code}, Payload = {res.json()}")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert len(data["full_name"]) > 0
    assert data["skills_count"] > 0
    assert data["projects_count"] >= 1


@pytest.mark.asyncio
async def test_get_and_update_profile_endpoints(test_client: AsyncClient):
    """Kiểm tra chuỗi truy vấn GET /api/v1/profile và cập nhật PUT /api/v1/profile."""
    logger.info("=== [TEST] Profile GET & PUT Endpoints Lifecycle ===")
    headers = {"X-Internal-Secret": settings.INTERNAL_API_SECRET}

    # 1. GET /api/v1/profile (sẽ tự động sync nếu DB trống)
    get_res = await test_client.get("/api/v1/profile", headers=headers)
    logger.info(f"  GET /profile Status = {get_res.status_code}")
    assert get_res.status_code == 200
    profile_data = get_res.json()
    logger.info(f"  Profile Fetched: Full Name='{profile_data['full_name']}', Headline='{profile_data['headline']}'")
    assert len(profile_data["full_name"]) > 0
    assert len(profile_data["skills"]) > 0
    assert len(profile_data["projects"]) >= 1

    # 2. PUT /api/v1/profile
    update_payload = {
        "headline": "DevOps & Cloud Infrastructure Engineer Intern",
        "location": "Ho Chi Minh City, Vietnam",
    }
    logger.info(f"  Sending PUT /profile update payload: {update_payload}")
    put_res = await test_client.put(
        "/api/v1/profile", json=update_payload, headers=headers
    )
    logger.info(f"  PUT /profile Response Status = {put_res.status_code}")
    assert put_res.status_code == 200
    updated_data = put_res.json()
    logger.info(f"  Updated Profile Headline: '{updated_data['headline']}'")
    assert updated_data["headline"] == "DevOps & Cloud Infrastructure Engineer Intern"
    assert updated_data["location"] == "Ho Chi Minh City, Vietnam"
    assert len(updated_data["skills"]) == len(profile_data["skills"])
    assert len(updated_data["projects"]) == len(profile_data["projects"])
