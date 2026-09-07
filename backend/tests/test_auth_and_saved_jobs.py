import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import (
    get_password_hash,
    verify_password,
    needs_password_rehash,
    create_access_token,
    decode_access_token,
)
from app.main import app
from app.models.candidate import Candidate
from app.models.job import Job, RawJob, JobStatusEnum, WorkModeEnum, JobLevelEnum
from app.models.resume import ApplicationLog, ApplicationChannelEnum, ApplicationStatusEnum, TailoredResume
from app.models.user import User
from app.models.saved_job import SavedJob
from app.services.notifications.notification_service import (
    NotificationPayload,
    NotificationService,
    ConsoleNotificationProvider,
)


@pytest_asyncio.fixture
async def test_session():
    """Tạo session engine SQLite in-memory."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def test_client():
    """Tạo TestClient với database SQLite in-memory."""
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


def test_password_hashing_and_verification():
    """Kiểm tra Argon2id hashing theo chuẩn OWASP và tương thích ngược PBKDF2."""
    password = "secure_password_123"
    hashed = get_password_hash(password)
    assert hashed.startswith("$argon2id$")
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False
    assert needs_password_rehash(hashed) is False

    # Kiểm tra tương thích ngược với hash PBKDF2 cũ
    legacy_pbkdf2 = "pbkdf2_sha256$100000$67b4458f7004f2dfcb3c2a6f7bca7a1d$04ff87271fc14cebf057e79cffba94ce799f920f4c02f06b6b7f32906d4e5f78"
    # Plain text tương ứng là "password123"
    import hashlib
    # Generate an explicit valid legacy hash for testing
    salt = "1234567890abcdef"
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()
    legacy_hash = f"pbkdf2_sha256$100000${salt}${key}"
    assert verify_password(password, legacy_hash) is True
    assert verify_password("wrong_pwd", legacy_hash) is False
    assert needs_password_rehash(legacy_hash) is True



def test_token_creation_and_decoding():
    """Kiểm tra tạo token PyJWT HS256 và giải mã."""
    sub_id = str(uuid.uuid4())
    data = {"sub": sub_id, "email": "test@example.com"}
    token = create_access_token(data)
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == sub_id
    assert decoded["email"] == "test@example.com"
    assert "exp" in decoded



@pytest.mark.asyncio
async def test_auth_register_and_login_flow(test_client: AsyncClient):
    """Kiểm tra luồng đăng ký, đăng nhập và lấy thông tin user."""
    # 1. Đăng ký tài khoản
    reg_payload = {
        "email": "user@example.com",
        "password": "password123",
        "full_name": "Nguyen Van A"
    }
    resp = await test_client.post("/api/v1/auth/register", json=reg_payload)
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "user@example.com"
    assert data["user"]["candidate_id"] is not None
    token = data["access_token"]

    # 2. Đăng nhập
    login_payload = {
        "email": "user@example.com",
        "password": "password123"
    }
    login_resp = await test_client.post("/api/v1/auth/login", json=login_payload)
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert "access_token" in login_data

    # 3. Lấy thông tin /me
    me_resp = await test_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == "user@example.com"
    assert me_data["full_name"] == "Nguyen Van A"

    # 4. Kiểm tra xác thực qua Query param (cho iframe/download PDF)
    query_resp = await test_client.get(
        f"/api/v1/jobs/saved?token={token}"
    )
    assert query_resp.status_code == 200


@pytest.mark.asyncio
async def test_saved_job_workflow(test_client: AsyncClient):
    """Kiểm tra lưu job, xem danh sách và hủy lưu job."""
    # 1. Đăng ký user và lấy token
    reg_resp = await test_client.post("/api/v1/auth/register", json={
        "email": "savedjob_tester@example.com",
        "password": "password123",
        "full_name": "Job Saver"
    })
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Thu thập job mock (yêu cầu internal secret vì có verify_admin_access)
    await test_client.post(
        "/api/v1/jobs/collect?source=mock&limit=2",
        headers={"X-Internal-Secret": settings.INTERNAL_API_SECRET},
    )
    
    # 3. Lấy danh sách job để chọn 1 job id
    jobs_resp = await test_client.get("/api/v1/jobs")
    assert jobs_resp.status_code == 200
    jobs_data = jobs_resp.json()
    assert len(jobs_data["items"]) > 0
    target_job_id = jobs_data["items"][0]["id"]

    # 4. Lưu job
    save_resp = await test_client.post(
        f"/api/v1/jobs/{target_job_id}/save",
        json={"notes": "Great internship opportunity"},
        headers=headers,
    )
    assert save_resp.status_code == 200
    assert save_resp.json()["status"] == "saved"

    # 5. Xem danh sách saved jobs
    saved_list_resp = await test_client.get("/api/v1/jobs/saved", headers=headers)
    assert saved_list_resp.status_code == 200
    saved_list = saved_list_resp.json()
    assert len(saved_list) == 1
    assert saved_list[0]["job_id"] == target_job_id
    assert saved_list[0]["notes"] == "Great internship opportunity"

    # 6. Hủy lưu job
    unsave_resp = await test_client.delete(f"/api/v1/jobs/{target_job_id}/save", headers=headers)
    assert unsave_resp.status_code == 200
    assert unsave_resp.json()["status"] == "unsaved"

    # 7. Kiểm tra danh sách rỗng
    saved_list_resp2 = await test_client.get("/api/v1/jobs/saved", headers=headers)
    assert len(saved_list_resp2.json()) == 0


@pytest.mark.asyncio
async def test_notification_service_dispatch():
    """Kiểm tra NotificationService gửi thông báo qua Console Provider."""
    service = NotificationService()
    payload = NotificationPayload(
        title="Test Notification",
        message="This is a test notification message",
        notification_type="INFO",
        action_url="http://localhost:3000/dashboard",
    )
    results = await service.notify(payload)
    assert results.get("ConsoleNotificationProvider") is True


@pytest.mark.asyncio
async def test_admin_superuser_bootstrap_and_permissions(test_client: AsyncClient):
    """Kiểm tra tài khoản cấu hình ADMIN_EMAIL tự động nhận quyền Superuser."""
    # 1. Đăng ký tài khoản với admin email
    admin_payload = {
        "email": settings.ADMIN_EMAIL,
        "password": settings.ADMIN_INITIAL_PASSWORD,
        "full_name": "Vy Quoc Huy Admin"
    }
    reg_resp = await test_client.post("/api/v1/auth/register", json=admin_payload)
    assert reg_resp.status_code == 201
    data = reg_resp.json()
    assert data["user"]["email"] == settings.ADMIN_EMAIL
    assert data["user"]["is_superuser"] is True
    admin_token = data["access_token"]

    # 2. Đăng ký một tài khoản thứ hai (user thường)
    user2_payload = {
        "email": "candidate.normal@example.com",
        "password": "password123",
        "full_name": "Normal Candidate"
    }
    u2_resp = await test_client.post("/api/v1/auth/register", json=user2_payload)
    assert u2_resp.status_code == 201
    u2_data = u2_resp.json()
    assert u2_data["user"]["is_superuser"] is False


@pytest.mark.asyncio
async def test_transparent_password_rehash_on_login(test_client: AsyncClient, test_session: AsyncSession):
    """
    Kiểm tra cơ chế nâng cấp mật khẩu trong suốt (Transparent Rehash):
    Khi user có hash PBKDF2 cũ đăng nhập thành công, hệ thống tự động băm lại bằng Argon2id.
    """
    import hashlib
    # 1. Tạo legacy PBKDF2 hash cho "legacy_pass123"
    plain_pass = "legacy_pass123"
    salt = "1234567890abcdef"
    key = hashlib.pbkdf2_hmac("sha256", plain_pass.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()
    legacy_hash = f"pbkdf2_sha256$100000${salt}${key}"

    # 2. Đăng ký tài khoản thường trước
    reg_payload = {
        "email": "legacy_user@example.com",
        "password": "temp_password_123",
        "full_name": "Legacy User",
    }
    await test_client.post("/api/v1/auth/register", json=reg_payload)

    # 3. Ép cập nhật hash của user này thành PBKDF2 cũ trong DB để giả lập user từ bản cũ
    from app.models.user import User
    from sqlalchemy import update, select
    from app.core.database import get_db

    # Lấy session override từ app
    session_override = app.dependency_overrides.get(get_db)
    async for s in session_override():
        await s.execute(
            update(User)
            .where(User.email == "legacy_user@example.com")
            .values(hashed_password=legacy_hash)
        )
        await s.commit()

        # Kiểm tra trước khi login: hash là PBKDF2
        u = (await s.execute(select(User).where(User.email == "legacy_user@example.com"))).scalar_one()
        assert u.hashed_password.startswith("pbkdf2_sha256$")
        break

    # 4. Đăng nhập với mật khẩu đúng "legacy_pass123"
    login_resp = await test_client.post(
        "/api/v1/auth/login",
        json={"email": "legacy_user@example.com", "password": plain_pass},
    )
    assert login_resp.status_code == 200

    # 5. Kiểm tra sau khi login: hash đã được tự động nâng cấp sang Argon2id!
    async for s in session_override():
        u = (await s.execute(select(User).where(User.email == "legacy_user@example.com"))).scalar_one()
        assert u.hashed_password.startswith("$argon2id$")
        assert verify_password(plain_pass, u.hashed_password) is True
        break

    # 6. Đăng nhập lần tiếp theo với hash Argon2id mới -> vẫn thành công
    login_resp2 = await test_client.post(
        "/api/v1/auth/login",
        json={"email": "legacy_user@example.com", "password": plain_pass},
    )
    assert login_resp2.status_code == 200


