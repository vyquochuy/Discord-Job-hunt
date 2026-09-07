import os
import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.main import app
from app.models.job import Job, JobLevelEnum, JobStatusEnum, RawJob, WorkModeEnum
from app.models.user import User


@pytest_asyncio.fixture
async def test_env():
    """Thiết lập môi trường in-memory SQLite biệt lập với client HTTP."""
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
        yield client, session_factory

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_multi_user_registration_and_profile_isolation(test_env):
    """
    1. Kiểm tra 2 người dùng đăng ký tài khoản riêng biệt.
    2. Kiểm tra hồ sơ (Profile) của mỗi người được cô lập 100%.
    """
    client, session_maker = test_env

    # 1. Đăng ký User A
    res_a = await client.post(
        "/api/v1/auth/register",
        json={"email": "alice@company.com", "password": "Password123!", "full_name": "Alice Johnson"},
    )
    assert res_a.status_code == 201
    token_a = res_a.json()["access_token"]
    cand_id_a = res_a.json()["user"]["candidate_id"]

    # 2. Đăng ký User B
    res_b = await client.post(
        "/api/v1/auth/register",
        json={"email": "bob@company.com", "password": "Password123!", "full_name": "Bob Smith"},
    )
    assert res_b.status_code == 201
    token_b = res_b.json()["access_token"]
    cand_id_b = res_b.json()["user"]["candidate_id"]

    assert cand_id_a != cand_id_b

    # 3. User A cập nhật profile của mình
    headers_a = {"Authorization": f"Bearer {token_a}"}
    res_update_a = await client.put(
        "/api/v1/profile",
        json={"headline": "Senior Python Architect", "phone": "0901111111", "location": "Hanoi"},
        headers=headers_a,
    )
    assert res_update_a.status_code == 200
    assert res_update_a.json()["headline"] == "Senior Python Architect"

    # 4. User B cập nhật profile của mình
    headers_b = {"Authorization": f"Bearer {token_b}"}
    res_update_b = await client.put(
        "/api/v1/profile",
        json={"headline": "DevOps / SRE Lead", "phone": "0902222222", "location": "Da Nang"},
        headers=headers_b,
    )
    assert res_update_b.status_code == 200
    assert res_update_b.json()["headline"] == "DevOps / SRE Lead"

    # 5. User A lấy lại profile -> Thấy đúng thông tin của Alice, không bị Bob đè
    res_get_a = await client.get("/api/v1/profile", headers=headers_a)
    assert res_get_a.status_code == 200
    assert res_get_a.json()["full_name"] == "Alice Johnson"
    assert res_get_a.json()["headline"] == "Senior Python Architect"
    assert res_get_a.json()["phone"] == "0901111111"

    # 6. User B lấy lại profile -> Thấy đúng thông tin của Bob, không dính của Alice
    res_get_b = await client.get("/api/v1/profile", headers=headers_b)
    assert res_get_b.status_code == 200
    assert res_get_b.json()["full_name"] == "Bob Smith"
    assert res_get_b.json()["headline"] == "DevOps / SRE Lead"
    assert res_get_b.json()["phone"] == "0902222222"


@pytest.mark.asyncio
async def test_multi_user_resume_and_file_sandbox_isolation(test_env):
    """
    1. User A và User B cùng tailor resume cho một Job X.
    2. Xác nhận 2 tệp PDF và TeX được lưu độc lập ở storage/resumes/{cand_A}/{job_X} và {cand_B}/{job_X}.
    3. User B dùng token của mình để truy cập Resume của User A (Malicious ID) -> BỊ TỪ CHỐI (404 Not Found).
    """
    client, session_maker = test_env

    # 1. Tạo Job X trong Database
    job_id = uuid.uuid4()
    async with session_maker() as session:
        raw_job = RawJob(
            source="mock",
            source_url=f"https://jobs.test/item/{job_id}",
            source_job_id=f"mock-{job_id}",
            content_hash=f"hash-{job_id}",
            raw_payload={"title": "Cloud Infrastructure Engineer"},
        )
        session.add(raw_job)
        await session.flush()

        job = Job(
            id=job_id,
            raw_job_id=raw_job.id,
            title="Cloud Infrastructure Engineer",
            normalized_title="cloud infrastructure engineer",
            company_name="VNG Corporation",
            normalized_company="vng corporation",
            location="Ho Chi Minh City",
            work_mode=WorkModeEnum.HYBRID,
            level=JobLevelEnum.MID,
            min_salary=25_000_000,
            max_salary=45_000_000,
            salary_currency="VND",
            status=JobStatusEnum.ACTIVE,
            description="Tìm kiếm kỹ sư Cloud & Hệ thống.",
        )
        session.add(job)
        await session.commit()

    # 2. Đăng ký Alice & Bob
    res_a = await client.post(
        "/api/v1/auth/register",
        json={"email": "alice_resume@test.com", "password": "Password123!", "full_name": "Alice Candidate"},
    )
    token_a = res_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    res_b = await client.post(
        "/api/v1/auth/register",
        json={"email": "bob_resume@test.com", "password": "Password123!", "full_name": "Bob Candidate"},
    )
    token_b = res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. Alice tailor resume cho Job X
    res_tailor_a = await client.post(
        f"/api/v1/resumes/tailor/{job_id}",
        json={"force_regenerate": True},
        headers=headers_a,
    )
    assert res_tailor_a.status_code == 200
    resume_a_data = res_tailor_a.json()
    resume_a_id = resume_a_data["id"]
    pdf_a_path = resume_a_data["pdf_path"]

    # 4. Bob tailor resume cho CÙNG Job X
    res_tailor_b = await client.post(
        f"/api/v1/resumes/tailor/{job_id}",
        json={"force_regenerate": True},
        headers=headers_b,
    )
    assert res_tailor_b.status_code == 200
    resume_b_data = res_tailor_b.json()
    resume_b_id = resume_b_data["id"]
    pdf_b_path = resume_b_data["pdf_path"]

    # Đảm bảo 2 resume ID khác nhau và 2 đường dẫn PDF nằm ở 2 thư mục sandbox khác nhau
    assert resume_a_id != resume_b_id
    assert pdf_a_path != pdf_b_path
    assert os.path.exists(pdf_a_path)
    assert os.path.exists(pdf_b_path)

    # 5. [MALICIOUS TEST 1] Bob cố tình GET resume của Alice bằng ID
    res_malicious_get = await client.get(f"/api/v1/resumes/{resume_a_id}", headers=headers_b)
    assert res_malicious_get.status_code == 404

    # 6. [MALICIOUS TEST 2] Bob cố tình tải file PDF của Alice
    res_malicious_pdf = await client.get(f"/api/v1/resumes/{resume_a_id}/pdf", headers=headers_b)
    assert res_malicious_pdf.status_code == 404

    # 7. [MALICIOUS TEST 3] Bob cố tình đọc source LaTeX (.tex) của Alice
    res_malicious_tex = await client.get(f"/api/v1/resumes/{resume_a_id}/tex", headers=headers_b)
    assert res_malicious_tex.status_code == 404

    # 8. [MALICIOUS TEST 4] Bob cố tình ghi đè mã LaTeX (.tex) của Alice
    res_malicious_put = await client.put(
        f"/api/v1/resumes/{resume_a_id}/tex",
        json={"latex_source": "Hacked source"},
        headers=headers_b,
    )
    assert res_malicious_put.status_code == 404

    # 9. [MALICIOUS TEST 5] Bob cố tình gửi DELETE resume của Alice
    res_malicious_del = await client.delete(f"/api/v1/resumes/{resume_a_id}", headers=headers_b)
    assert res_malicious_del.status_code == 404

    # Xác nhận resume của Alice vẫn tồn tại nguyên vẹn
    res_verify_a = await client.get(f"/api/v1/resumes/{resume_a_id}", headers=headers_a)
    assert res_verify_a.status_code == 200


@pytest.mark.asyncio
async def test_multi_user_applications_and_idor_protection(test_env):
    """
    1. User A nộp đơn cho Job X -> Tạo ApplicationLog.
    2. User B nộp đơn cho Job X -> Vẫn nộp thành công (không bị User A chặn idempotency).
    3. User B xem danh sách đơn ứng tuyển -> Chỉ thấy của mình.
    4. User B cố tình xem / sửa trạng thái ApplicationLog của User A -> BỊ TỪ CHỐI (404 Not Found).
    """
    client, session_maker = test_env

    # 1. Tạo Job Y
    job_id = uuid.uuid4()
    async with session_maker() as session:
        raw_job = RawJob(
            source="mock",
            source_url=f"https://jobs.test/item/{job_id}",
            source_job_id=f"mock-{job_id}",
            content_hash=f"hash-{job_id}",
            raw_payload={"title": "Security Engineer"},
        )
        session.add(raw_job)
        await session.flush()

        job = Job(
            id=job_id,
            raw_job_id=raw_job.id,
            title="Security Engineer",
            normalized_title="security engineer",
            company_name="Viettel Cyber Security",
            normalized_company="viettel cyber security",
            location="Hanoi",
            work_mode=WorkModeEnum.ONSITE,
            level=JobLevelEnum.SENIOR,
            min_salary=30_000_000,
            max_salary=60_000_000,
            salary_currency="VND",
            status=JobStatusEnum.ACTIVE,
            description="Tìm kiếm chuyên gia ATTT.",
        )
        session.add(job)
        await session.commit()

    # 2. Đăng ký User A và User B
    res_a = await client.post(
        "/api/v1/auth/register",
        json={"email": "alice_app@test.com", "password": "Password123!", "full_name": "Alice App"},
    )
    headers_a = {"Authorization": f"Bearer {res_a.json()['access_token']}"}

    res_b = await client.post(
        "/api/v1/auth/register",
        json={"email": "bob_app@test.com", "password": "Password123!", "full_name": "Bob App"},
    )
    headers_b = {"Authorization": f"Bearer {res_b.json()['access_token']}"}

    # 3. User A nộp đơn cho Job Y
    res_apply_a = await client.post(f"/api/v1/applications/apply/{job_id}", headers=headers_a)
    assert res_apply_a.status_code == 200
    app_a_id = res_apply_a.json()["id"]

    # 4. User B cũng nộp đơn cho Job Y -> Thành công (không bị nhầm là đã nộp)
    res_apply_b = await client.post(f"/api/v1/applications/apply/{job_id}", headers=headers_b)
    assert res_apply_b.status_code == 200
    app_b_id = res_apply_b.json()["id"]
    assert app_a_id != app_b_id

    # 5. User A xem danh sách applications -> Chỉ thấy 1 đơn của chính mình
    res_list_a = await client.get("/api/v1/applications", headers=headers_a)
    assert res_list_a.status_code == 200
    assert len(res_list_a.json()) == 1
    assert res_list_a.json()[0]["id"] == app_a_id

    # 6. User B xem danh sách applications -> Chỉ thấy 1 đơn của chính mình
    res_list_b = await client.get("/api/v1/applications", headers=headers_b)
    assert res_list_b.status_code == 200
    assert len(res_list_b.json()) == 1
    assert res_list_b.json()[0]["id"] == app_b_id

    # 7. [MALICIOUS ID] User B cố tình GET chi tiết đơn của User A
    res_malicious_app_get = await client.get(f"/api/v1/applications/{app_a_id}", headers=headers_b)
    assert res_malicious_app_get.status_code == 404

    # 8. [MALICIOUS ID] User B cố tình PATCH đổi trạng thái đơn của User A
    res_malicious_app_patch = await client.patch(
        f"/api/v1/applications/{app_a_id}/status",
        json={"status": "REJECTED"},
        headers=headers_b,
    )
    assert res_malicious_app_patch.status_code == 404


@pytest.mark.asyncio
async def test_superuser_sync_restriction(test_env):
    """
    Kiểm tra /api/v1/profile/sync chỉ cho phép Superuser, từ chối người dùng thông thường (403 Forbidden).
    """
    client, session_maker = test_env

    # 1. Đăng ký tài khoản thường (User 2)
    # Lưu ý: User đầu tiên đăng ký sẽ tự động là Superuser trong hệ thống
    res_first = await client.post(
        "/api/v1/auth/register",
        json={"email": "first_admin@test.com", "password": "Password123!", "full_name": "First Admin"},
    )
    token_admin = res_first.json()["access_token"]
    assert res_first.json()["user"]["is_superuser"] is True

    res_regular = await client.post(
        "/api/v1/auth/register",
        json={"email": "regular_user@test.com", "password": "Password123!", "full_name": "Regular User"},
    )
    token_regular = res_regular.json()["access_token"]
    assert res_regular.json()["user"]["is_superuser"] is False

    # 2. Regular user gọi POST /profile/sync -> Bị 403 Forbidden
    headers_regular = {"Authorization": f"Bearer {token_regular}"}
    res_sync_regular = await client.post("/api/v1/profile/sync", headers=headers_regular)
    assert res_sync_regular.status_code == 403

    # 3. Superuser gọi POST /profile/sync -> Được phép (200 OK)
    headers_admin = {"Authorization": f"Bearer {token_admin}"}
    res_sync_admin = await client.post("/api/v1/profile/sync", headers=headers_admin)
    assert res_sync_admin.status_code == 200
