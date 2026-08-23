import pytest
import pytest_asyncio
import uuid
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.models.candidate import Candidate, CandidateProject
from app.models.job import Job, JobLevelEnum, RawJob, WorkModeEnum
from app.models.resume import CoverLetter, ResumeStatusEnum, TailoredResume


@pytest_asyncio.fixture
async def test_client():
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
async def test_delete_tailored_resume_by_job_id(test_client):
    """Kiểm tra xóa Tailored Resume và Cover Letter của một Job."""
    client, session_maker = test_client
    headers = {"X-Internal-Secret": settings.INTERNAL_API_SECRET}

    job_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    async with session_maker() as session:
        cand = Candidate(
            id=candidate_id,
            full_name="Nguyen Van A",
            headline="Intern",
            email="a@example.com",
        )
        raw_job = RawJob(
            id=uuid.uuid4(),
            source="mock",
            source_url="https://example.com/job",
            content_hash="mock_hash_system_test",
        )
        job = Job(
            id=job_id,
            raw_job_id=raw_job.id,
            title="Backend Intern",
            normalized_title="backend intern",
            company_name="CloudOps Tech",
            normalized_company="cloudops tech",
            description="Python FastAPI backend intern",
            work_mode=WorkModeEnum.HYBRID,
            level=JobLevelEnum.INTERN,
        )
        resume = TailoredResume(
            candidate_id=cand.id,
            job_id=job.id,
            target_title="Backend Intern",
            latex_source=r"\documentclass{article}\begin{document}Test Resume\end{document}",
            status=ResumeStatusEnum.COMPILED,
        )
        session.add_all([cand, raw_job, job, resume])
        await session.flush()

        cl = CoverLetter(
            tailored_resume_id=resume.id,
            candidate_id=cand.id,
            job_id=job.id,
            company_name="CloudOps Tech",
            salutation="Dear Team,",
            content_markdown="# Cover Letter\nSample markdown",
        )
        session.add(cl)
        await session.commit()

    # 1. DELETE /api/v1/resumes/job/{job_id}
    del_res = await client.delete(f"/api/v1/resumes/job/{job_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "success"

    # 2. Query lại -> 404 Not Found
    get_res = await client.get(f"/api/v1/resumes/job/{job_id}", headers=headers)
    assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_system_purge_database_endpoint(test_client):
    """Kiểm tra endpoint POST /api/v1/system/purge-database."""
    client, session_maker = test_client
    headers = {"X-Internal-Secret": settings.INTERNAL_API_SECRET}

    # 1. Gọi không confirm -> 400 Bad Request
    res_no_confirm = await client.post(
        "/api/v1/system/purge-database",
        json={"scope": "tailoring_only", "confirm": False},
        headers=headers,
    )
    assert res_no_confirm.status_code == 400

    # 2. Gọi confirm=True scope='tailoring_only' -> 200 OK
    res_purge = await client.post(
        "/api/v1/system/purge-database",
        json={"scope": "tailoring_only", "clean_storage": True, "confirm": True},
        headers=headers,
    )
    assert res_purge.status_code == 200
    data = res_purge.json()
    assert data["status"] == "success"
    assert data["scope"] == "tailoring_only"


@pytest.mark.asyncio
async def test_system_reset_demo_endpoint(test_client):
    """Kiểm tra endpoint POST /api/v1/system/reset-demo."""
    client, session_maker = test_client
    headers = {"X-Internal-Secret": settings.INTERNAL_API_SECRET}

    res_reset = await client.post("/api/v1/system/reset-demo", headers=headers)
    assert res_reset.status_code == 200
    data = res_reset.json()
    assert data["status"] == "success"
    assert "candidate_profile" in data
