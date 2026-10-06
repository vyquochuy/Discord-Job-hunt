import asyncio
import os
import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.main import app
from app.models.candidate import Candidate, CandidateProject
from app.models.job import Job, JobLevelEnum, JobStatusEnum, RawJob, WorkModeEnum
from app.models.resume import ResumeStatusEnum, TailoredResume
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
async def test_candidate_profile_unassigned_stealing_regression(test_env):
    """
    REGRESSION TEST:
    Đảm bảo khi có Candidate profile unassigned trong DB (chưa có user_id),
    người dùng mới đăng ký KHÔNG ĐƯỢC PHÉP chiếm đoạt profile này.
    Người dùng mới bắt buộc phải được tạo một Candidate profile mới độc lập.
    """
    client, session_maker = test_env

    # 1. Tạo một unassigned Candidate (ví dụ từ file seed context/)
    unassigned_cand_id = uuid.uuid4()
    async with session_maker() as session:
        seed_candidate = Candidate(
            id=unassigned_cand_id,
            user_id=None,
            full_name="Confidential Seed Candidate",
            email="seed@secret.internal",
            headline="Principal Security Architect",
            summary="Confidential executive profile with proprietary facts.",
        )
        session.add(seed_candidate)
        await session.commit()

    # 2. Người dùng mới đăng ký qua API
    res_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "attacker@outside.com", "password": "Password123!", "full_name": "Attacker Name"},
    )
    assert res_reg.status_code == 201
    user_cand_id = res_reg.json()["user"]["candidate_id"]

    # 3. Khẳng định: Người dùng mới KHÔNG ĐƯỢC gán profile unassigned_cand_id
    assert user_cand_id != str(unassigned_cand_id), (
        f"Security Violation: New user hijacked unassigned candidate {unassigned_cand_id}!"
    )

    # 4. Profile unassigned vẫn phải được giữ nguyên trạng, không bị user_id của người mới chiếm đoạt
    async with session_maker() as session:
        check_seed = await session.get(Candidate, unassigned_cand_id)
        assert check_seed is not None
        assert check_seed.user_id is None, "Seed candidate user_id was hijacked!"

        # Kiểm tra candidate của user mới là một record độc lập hoàn toàn
        new_cand = await session.get(Candidate, uuid.UUID(user_cand_id))
        assert new_cand is not None
        assert new_cand.full_name == "Attacker Name"
        assert new_cand.email == "attacker@outside.com"


@pytest.mark.asyncio
async def test_resume_pdf_download_bola_and_query_token_auth(test_env, tmp_path):
    """
    REGRESSION TEST:
    1. Endpoint GET /api/v1/resumes/{id}/pdf KHÔNG được phép truy cập công khai không xác thực (401).
    2. User B KHÔNG được phép tải hoặc xem trước PDF của User A (404/403).
    3. User A có thể tải bằng Bearer token (200).
    4. User A có thể xem trước bằng Query param ?token= (cho iframe) (200).
    5. User B KHÔNG thể dùng token của mình trong query param để xem PDF của User A (404/403).
    """
    client, session_maker = test_env

    # 1. Tạo Job
    job_id = uuid.uuid4()
    async with session_maker() as session:
        raw_job = RawJob(
            source="mock",
            source_url="https://jobs.test/1",
            source_job_id="mock-1",
            content_hash="hash-1",
            raw_payload={"title": "Go Engineer"},
        )
        session.add(raw_job)
        await session.flush()
        job = Job(
            id=job_id,
            raw_job_id=raw_job.id,
            title="Go Engineer",
            normalized_title="go engineer",
            company_name="Acme Corp",
            normalized_company="acme corp",
            location="Remote",
            work_mode=WorkModeEnum.REMOTE,
            level=JobLevelEnum.MID,
            min_salary=20_000_000,
            max_salary=40_000_000,
            salary_currency="VND",
            status=JobStatusEnum.ACTIVE,
            description="Golang microservices.",
        )
        session.add(job)
        await session.commit()

    # 2. Đăng ký Alice và Bob
    res_a = await client.post(
        "/api/v1/auth/register",
        json={"email": "alice_pdf@test.com", "password": "Password123!", "full_name": "Alice PDF"},
    )
    assert res_a.status_code == 201
    token_a = res_a.json()["access_token"]
    user_a_cand_id = uuid.UUID(res_a.json()["user"]["candidate_id"])

    res_b = await client.post(
        "/api/v1/auth/register",
        json={"email": "bob_pdf@test.com", "password": "Password123!", "full_name": "Bob PDF"},
    )
    assert res_b.status_code == 201
    token_b = res_b.json()["access_token"]
    user_b_cand_id = uuid.UUID(res_b.json()["user"]["candidate_id"])

    # 3. Tạo một Tailored Resume trực tiếp cho Alice với file PDF hợp lệ trên disk
    resume_a_id = uuid.uuid4()
    fake_pdf = tmp_path / "alice_resume.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4\nAlice Private Resume\n%%EOF")

    async with session_maker() as session:
        resume_a = TailoredResume(
            id=resume_a_id,
            candidate_id=user_a_cand_id,
            job_id=job_id,
            target_title="Go Engineer",
            latex_source="\\documentclass{article}\\begin{document}Alice\\end{document}",
            pdf_path=str(fake_pdf),
            status=ResumeStatusEnum.COMPILED,
            provenance_score=100.0,
            is_provenance_verified=True,
        )
        session.add(resume_a)
        await session.commit()

    # --- KIỂM THỬ BẢO MẬT ---

    # Case 1: Anonymous / Unauthenticated gọi tới PDF của Alice -> PHẢI BỊ TỪ CHỐI (401 Unauthorized)
    res_anon = await client.get(f"/api/v1/resumes/{resume_a_id}/pdf")
    assert res_anon.status_code == 401, (
        f"Security Failure: Unauthenticated user accessed PDF! Got {res_anon.status_code}"
    )

    # Case 2: Bob (User B) dùng Bearer Token của mình cố tình lấy PDF của Alice -> PHẢI BỊ TỪ CHỐI (404 Not Found)
    res_bob = await client.get(
        f"/api/v1/resumes/{resume_a_id}/pdf",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_bob.status_code == 404, (
        f"Security Failure: Bob accessed Alice's PDF with Bearer token! Got {res_bob.status_code}"
    )

    # Case 3: Bob (User B) dùng Query Token của mình cố tình lấy PDF của Alice -> PHẢI BỊ TỪ CHỐI (404 Not Found)
    res_bob_query = await client.get(
        f"/api/v1/resumes/{resume_a_id}/pdf?token={token_b}"
    )
    assert res_bob_query.status_code == 404, (
        f"Security Failure: Bob accessed Alice's PDF with Query token! Got {res_bob_query.status_code}"
    )

    # Case 4: Alice (User A) dùng Bearer Token -> ĐƯỢC PHÉP (200 OK)
    res_alice_bearer = await client.get(
        f"/api/v1/resumes/{resume_a_id}/pdf",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_alice_bearer.status_code == 200
    assert res_alice_bearer.content == b"%PDF-1.4\nAlice Private Resume\n%%EOF"

    # Case 5: Alice (User A) dùng Query Token (iframe embed) -> ĐƯỢC PHÉP (200 OK)
    res_alice_query = await client.get(
        f"/api/v1/resumes/{resume_a_id}/pdf?token={token_a}"
    )
    assert res_alice_query.status_code == 200
    assert res_alice_query.content == b"%PDF-1.4\nAlice Private Resume\n%%EOF"


@pytest.mark.asyncio
async def test_concurrent_registration_email_collision_handling(test_env):
    """
    REGRESSION TEST:
    Kiểm tra khi có 2 request đăng ký cùng email diễn ra đồng thời:
    - 1 request thành công 201 Created.
    - 1 request nhận 400 Bad Request một cách an toàn, KHÔNG được crash 500 Internal Server Error.
    """
    client, _ = test_env

    # Chạy đồng thời 2 request đăng ký cùng 1 email
    req1 = client.post(
        "/api/v1/auth/register",
        json={"email": "collision@test.com", "password": "Password123!", "full_name": "User One"},
    )
    req2 = client.post(
        "/api/v1/auth/register",
        json={"email": "collision@test.com", "password": "Password123!", "full_name": "User Two"},
    )

    results = await asyncio.gather(req1, req2, return_exceptions=True)

    status_codes = [r.status_code for r in results if not isinstance(r, Exception)]
    assert 201 in status_codes
    assert 400 in status_codes
    assert 500 not in status_codes
