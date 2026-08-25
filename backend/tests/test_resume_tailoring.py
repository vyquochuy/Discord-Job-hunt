import io
import logging
import pytest
import pytest_asyncio
import uuid
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.models.job import Job, JobLevelEnum, JobStatusEnum, RawJob, RawJobStatusEnum, WorkModeEnum
from app.models.resume import (
    ApplicationChannelEnum,
    ApplicationLog,
    ApplicationStatusEnum,
    ResumeStatusEnum,
    TailoredResume,
)
from app.repositories.candidate import CandidateRepository
from app.services.candidate import CandidateService
from app.services.tailoring.cover_letter_generator import cover_letter_generator
from app.services.tailoring.latex_compiler import latex_compiler
from app.services.tailoring.latex_generator import latex_generator
from app.services.tailoring.provenance_verifier import provenance_verifier
from app.services.tailoring.resume_service import resume_service
from app.services.tailoring.application_service import application_service

logger = logging.getLogger("test.resume_tailoring")


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
        yield client, session_factory

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture
async def setup_candidate_and_job(test_client):
    """Fixture chuẩn bị dữ liệu ứng viên và công việc mẫu để test."""
    client, session_maker = test_client

    async with session_maker() as session:
        # 1. Sync candidate từ context
        await CandidateService.sync_profile_from_context(session)
        candidate = await CandidateRepository.get_profile(session)

        # 2. Tạo raw job và công việc mẫu phù hợp (DevOps / System Intern)
        raw_job = RawJob(
            source="mock",
            source_url="https://cloudops.vn/careers/intern-sys",
            source_job_id="cloudops-intern-1",
            content_hash="mock-hash-cloudops-1",
            raw_payload={"title": "System & Cloud Infrastructure Intern"},
            fetch_status="PARSED",
        )
        session.add(raw_job)
        await session.flush()

        job = Job(
            raw_job_id=raw_job.id,
            title="System & Cloud Infrastructure Intern",
            normalized_title="System & Cloud Infrastructure Intern",
            company_name="CloudOps Technologies",
            normalized_company="CloudOps Technologies",
            location="Ho Chi Minh City",
            work_mode=WorkModeEnum.HYBRID,
            level=JobLevelEnum.INTERN,
            status=JobStatusEnum.ACTIVE,
            description=(
                "We are looking for a System & Cloud Infrastructure Intern. "
                "Requirements: Python, Docker, Linux, Git, PostgreSQL. "
                "Knowledge of serverless, cloud platforms, and security is a plus."
            ),
            contact_email="recruitment@cloudops.vn",
            apply_url="https://cloudops.vn/careers/intern-sys",
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)

        return candidate, job


@pytest.mark.asyncio
async def test_provenance_verifier_evidence_checking(setup_candidate_and_job):
    """
    Kiểm tra Provenance Verifier:
    - Bắt đúng các facts có thật trong context.
    - Phát hiện và cảnh báo các con số / số liệu bịa đặt (hallucinations).
    """
    logger.info("=== [TEST] Provenance Verifier Evidence Checking ===")
    candidate, job = setup_candidate_and_job

    # 1. Claim thật từ context (VYVYCHAT / E2EE / 45ms)
    true_claim = (
        "Architected zero-knowledge messaging platform with WebSockets achieving ~45ms round-trip latency."
    )
    # 2. Claim bịa đặt số liệu không có trong context (vd: managed 50 engineers, 99.999% uptime)
    fake_claim = (
        "Managed a team of 50 senior engineers and maintained 99.999% high availability uptime."
    )

    test_sections = {
        "PROJECTS": [true_claim, fake_claim],
    }

    evidence_items, provenance_score, is_verified = provenance_verifier.verify_resume(
        candidate=candidate,
        tailored_sections=test_sections,
    )

    assert len(evidence_items) == 2
    assert evidence_items[0].is_verified is True
    assert evidence_items[0].similarity_score > 0.6

    # Fake claim phải bị đánh dấu hoặc có điểm tương đồng thấp
    assert evidence_items[1].is_verified is False or evidence_items[1].similarity_score < 0.6
    logger.info(f"Provenance items checked: Score={provenance_score}, Verified={is_verified}")


@pytest.mark.asyncio
async def test_latex_generator_and_compiler(setup_candidate_and_job):
    """
    Kiểm tra LaTeX Generator sinh mã nguồn hợp lệ và LaTeX Compiler tạo file PDF.
    """
    logger.info("=== [TEST] LaTeX Generator & Compiler ===")
    candidate, job = setup_candidate_and_job

    matched_skills = ["Python", "Docker", "Linux", "PostgreSQL"]

    # 1. Sinh LaTeX
    latex_code = latex_generator.generate_tailored_tex(
        candidate=candidate,
        job=job,
        matched_skills=matched_skills,
        target_title="System Intern",
    )

    assert "\\documentclass" in latex_code
    assert "\\begin{document}" in latex_code
    assert "\\end{document}" in latex_code
    assert candidate.full_name in latex_code
    assert "System Intern" in latex_code

    # 2. Biên dịch TeX thành PDF
    success, pdf_path, error_msg = await latex_compiler.compile_tex(
        tex_content=latex_code,
        job_id=str(job.id),
        file_prefix="test_resume",
    )

    assert success is True
    assert pdf_path is not None
    logger.info(f"LaTeX Compilation Result: success={success}, pdf_path={pdf_path}")


@pytest.mark.asyncio
async def test_cover_letter_generation(setup_candidate_and_job):
    """
    Kiểm tra Cover Letter Generator sinh nội dung Markdown chuẩn mực, chân thực.
    """
    logger.info("=== [TEST] Cover Letter Generator ===")
    candidate, job = setup_candidate_and_job

    cl_data = cover_letter_generator.generate_cover_letter(
        candidate=candidate,
        job=job,
        matched_skills=["Python", "Linux", "Docker"],
    )

    assert cl_data["company_name"] == "CloudOps Technologies"
    assert "CloudOps Technologies" in cl_data["hook_statement"]
    assert "AI Job Hunter" in cl_data["content_markdown"] or "VYVYCHAT" in cl_data["content_markdown"]
    assert "Sincerely" in cl_data["content_markdown"]
    assert candidate.full_name in cl_data["content_markdown"]
    logger.info("Cover letter generated successfully.")


@pytest.mark.asyncio
async def test_resume_service_full_tailoring(test_client, setup_candidate_and_job):
    """
    Kiểm tra toàn bộ luồng ResumeTailorService.tailor_resume_for_job().
    """
    logger.info("=== [TEST] Resume Service Full Tailoring Flow ===")
    client, session_maker = test_client
    candidate, job = setup_candidate_and_job

    async with session_maker() as session:
        tailored_resume = await resume_service.tailor_resume_for_job(
            session=session,
            job_id=job.id,
            candidate_id=candidate.id,
            force_regenerate=True,
        )

        assert tailored_resume is not None
        assert tailored_resume.job_id == job.id
        assert tailored_resume.candidate_id == candidate.id
        assert tailored_resume.status in (ResumeStatusEnum.COMPILED, ResumeStatusEnum.DRAFT)
        assert tailored_resume.provenance_score >= 80.0
        assert len(tailored_resume.latex_source) > 100
        assert tailored_resume.cover_letter is not None
        assert tailored_resume.cover_letter.company_name == "CloudOps Technologies"
        assert len(tailored_resume.evidence_items) > 0

        logger.info(
            f"Tailored Resume ID={tailored_resume.id}, Status={tailored_resume.status}, "
            f"ProvenanceScore={tailored_resume.provenance_score}%, "
            f"EvidenceCount={len(tailored_resume.evidence_items)}"
        )


@pytest.mark.asyncio
async def test_application_service_dispatch(test_client, setup_candidate_and_job):
    """
    Kiểm tra ApplicationService.submit_application() và tính idempotent.
    """
    logger.info("=== [TEST] Application Service Submission & Idempotency ===")
    client, session_maker = test_client
    candidate, job = setup_candidate_and_job

    async with session_maker() as session:
        # Lần 1: Submit application (simulate_only=True)
        app_log = await application_service.submit_application(
            session=session,
            job_id=job.id,
            channel=ApplicationChannelEnum.EMAIL,
            recipient_email="hr@cloudops.vn",
            simulate_only=True,
        )

        assert app_log is not None
        assert app_log.status == ApplicationStatusEnum.READY
        assert app_log.recipient_email == "hr@cloudops.vn"

        # Lần 2: Submit thật (simulate_only=False)
        app_log_sent = await application_service.submit_application(
            session=session,
            job_id=job.id,
            channel=ApplicationChannelEnum.EMAIL,
            simulate_only=False,
        )

        assert app_log_sent.status == ApplicationStatusEnum.SENT
        assert app_log_sent.sent_at is not None

        # Lần 3: Gọi lại submit (phải trả về đúng bản log đã gửi trước đó - Idempotency)
        app_log_duplicate = await application_service.submit_application(
            session=session,
            job_id=job.id,
            simulate_only=False,
        )
        assert app_log_duplicate.id == app_log_sent.id
        logger.info(f"Application sent successfully: ID={app_log_sent.id}, Status={app_log_sent.status}")


@pytest.mark.asyncio
async def test_resumes_and_applications_rest_apis(test_client, setup_candidate_and_job):
    """
    Kiểm tra trọn bộ REST API endpoints cho Resumes và Applications.
    """
    logger.info("=== [TEST] REST API Endpoints Lifecycle for Phase 4 ===")
    client, session_maker = test_client
    candidate, job = setup_candidate_and_job
    headers = {"X-Internal-Secret": settings.INTERNAL_API_SECRET}

    # 1. POST /api/v1/resumes/tailor/{job_id}
    res_tailor = await client.post(
        f"/api/v1/resumes/tailor/{job.id}",
        json={"force_regenerate": True, "custom_tone": "professional_and_humble"},
        headers=headers,
    )
    assert res_tailor.status_code == 200
    tailor_data = res_tailor.json()
    resume_id = tailor_data["id"]
    assert tailor_data["job_id"] == str(job.id)
    assert tailor_data["target_title"] == job.title
    assert tailor_data["provenance_score"] >= 80.0
    assert "cover_letter" in tailor_data
    assert tailor_data["cover_letter"] is not None

    # 2. GET /api/v1/resumes/{id}
    res_get = await client.get(f"/api/v1/resumes/{resume_id}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["id"] == resume_id

    # 3. GET /api/v1/resumes/job/{job_id}
    res_get_job = await client.get(f"/api/v1/resumes/job/{job.id}", headers=headers)
    assert res_get_job.status_code == 200
    assert res_get_job.json()["id"] == resume_id

    # 4. GET /api/v1/resumes/{id}/tex
    res_tex = await client.get(f"/api/v1/resumes/{resume_id}/tex", headers=headers)
    assert res_tex.status_code == 200
    assert "\\documentclass" in res_tex.text

    # 5. GET /api/v1/resumes/{id}/pdf (inline vs attachment)
    res_pdf_inline = await client.get(f"/api/v1/resumes/{resume_id}/pdf?download=false", headers=headers)
    assert res_pdf_inline.status_code == 200
    assert res_pdf_inline.headers["content-type"] == "application/pdf"
    assert "inline" in res_pdf_inline.headers.get("content-disposition", "")
    assert len(res_pdf_inline.content) > 0

    res_pdf_attach = await client.get(f"/api/v1/resumes/{resume_id}/pdf?download=true", headers=headers)
    assert res_pdf_attach.status_code == 200
    assert "attachment" in res_pdf_attach.headers.get("content-disposition", "")

    # 5.1 PUT /api/v1/resumes/{id}/tex (Cập nhật và biên dịch lại LaTeX)
    updated_tex = res_tex.text.replace("Vy Quoc Huy", "Vy Quoc Huy - Senior")
    res_put_tex = await client.put(
        f"/api/v1/resumes/{resume_id}/tex",
        json={"latex_source": updated_tex},
        headers=headers,
    )
    assert res_put_tex.status_code == 200
    assert "Vy Quoc Huy - Senior" in res_put_tex.json()["latex_source"]

    # 6. POST /api/v1/applications/apply/{job_id}
    res_apply = await client.post(
        f"/api/v1/applications/apply/{job.id}",
        json={"channel": "EMAIL", "simulate_only": False},
        headers=headers,
    )
    assert res_apply.status_code == 200
    app_data = res_apply.json()
    app_id = app_data["id"]
    assert app_data["status"] == "SENT"
    assert app_data["job_id"] == str(job.id)

    # 7. GET /api/v1/applications
    res_apps = await client.get("/api/v1/applications", headers=headers)
    assert res_apps.status_code == 200
    assert len(res_apps.json()) >= 1

    # 8. GET /api/v1/applications/{id}
    res_app_detail = await client.get(f"/api/v1/applications/{app_id}", headers=headers)
    assert res_app_detail.status_code == 200
    assert res_app_detail.json()["id"] == app_id
    logger.info("All Phase 4 REST API endpoints verified successfully!")
