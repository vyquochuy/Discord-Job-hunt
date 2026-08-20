import logging
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.main import app
from app.models.job import Job, JobSkill, RawJob, Skill
from app.services.collectors.mock_adapter import MockJobCollector
from app.services.ingestion_pipeline import ingestion_pipeline

logger = logging.getLogger("test.pipeline")


@pytest_asyncio.fixture
async def async_db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def test_client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

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
async def test_ingestion_pipeline_e2e(async_db_session: AsyncSession):
    """Kiểm tra toàn bộ quy trình cào, lưu raw_jobs, chuẩn hóa và lưu jobs."""
    logger.info("=== [TEST] End-to-End Ingestion Pipeline Execution ===")
    collector = MockJobCollector()

    # 1. Lần chạy đầu tiên: cào 3 jobs mới
    logger.info("--- Step 1: First Run (Ingesting 3 new jobs) ---")
    stats_1 = await ingestion_pipeline.run(collector, async_db_session, limit=3)
    logger.info(f"  First Run Report: Fetched={stats_1.total_fetched}, Created={stats_1.created}, Unchanged={stats_1.unchanged}")
    
    assert stats_1.total_fetched == 3
    assert stats_1.created == 3
    assert stats_1.unchanged == 0
    assert stats_1.errors == 0

    # Kiểm tra database
    raw_res = await async_db_session.execute(select(RawJob))
    raw_jobs = raw_res.scalars().all()
    logger.info(f"  Verified Raw Jobs in DB: {len(raw_jobs)} records, all status=PARSED")
    assert len(raw_jobs) == 3
    assert all(r.fetch_status == "PARSED" for r in raw_jobs)

    jobs_res = await async_db_session.execute(select(Job))
    jobs = jobs_res.scalars().all()
    logger.info(f"  Verified Standardized Jobs in DB: {len(jobs)} records")
    assert len(jobs) == 3

    # Kiểm tra chuẩn hóa company
    fpt_job = next(j for j in jobs if "FPT" in j.company_name)
    logger.info(f"  Normalized Job Check: Title='{fpt_job.normalized_title}', Company='{fpt_job.normalized_company}'")
    assert fpt_job.normalized_company == "FPT Software"
    assert fpt_job.normalized_title == "Senior Python Backend Engineer"

    # Kiểm tra skills được liên kết
    skills_res = await async_db_session.execute(select(JobSkill).where(JobSkill.job_id == fpt_job.id))
    job_skills = skills_res.scalars().all()
    logger.info(f"  Associated JobSkills count for FPT Job: {len(job_skills)}")
    assert len(job_skills) >= 5

    # 2. Lần chạy thứ hai với dữ liệu không đổi: content_hash trùng khớp -> 0 cost LLM
    logger.info("--- Step 2: Second Run (Content Hash Cache Hit - 0 Token Cost) ---")
    stats_2 = await ingestion_pipeline.run(collector, async_db_session, limit=3)
    logger.info(f"  Second Run Report: Fetched={stats_2.total_fetched}, Created={stats_2.created}, Unchanged={stats_2.unchanged} (Cache Hit!)")
    assert stats_2.total_fetched == 3
    assert stats_2.created == 0
    assert stats_2.unchanged == 3
    assert stats_2.duplicates_detected == 0


@pytest.mark.asyncio
async def test_jobs_api_endpoints(test_client: AsyncClient):
    """Kiểm tra các endpoint REST API: POST /collect, GET /jobs, GET /jobs/{id}."""
    logger.info("=== [TEST] Jobs REST API Endpoints ===")
    
    # 1. Trigger collect mock jobs
    logger.info("--- 1. Testing POST /api/v1/jobs/collect?source=mock&limit=3 ---")
    collect_res = await test_client.post("/api/v1/jobs/collect?source=mock&limit=3")
    logger.info(f"  Response Status: {collect_res.status_code}, Body: {collect_res.json()}")
    assert collect_res.status_code == 200
    report = collect_res.json()["report"]
    assert report["created"] == 3

    # 2. GET /api/v1/jobs
    logger.info("--- 2. Testing GET /api/v1/jobs ---")
    list_res = await test_client.get("/api/v1/jobs")
    data = list_res.json()
    logger.info(f"  Total Jobs Found: {data['total']}, Page: {data['page']}, Items Count: {len(data['items'])}")
    assert list_res.status_code == 200
    assert data["total"] == 3
    assert len(data["items"]) == 3

    job_id = data["items"][0]["id"]

    # 3. GET /api/v1/jobs/{id}
    logger.info(f"--- 3. Testing GET /api/v1/jobs/{job_id} ---")
    detail_res = await test_client.get(f"/api/v1/jobs/{job_id}")
    detail = detail_res.json()
    logger.info(f"  Job Detail: Title='{detail['title']}', Company='{detail['company_name']}', Skills Count={len(detail['skills'])}")
    assert detail_res.status_code == 200
    assert detail["id"] == job_id
    assert "raw_job" in detail
    assert "skills" in detail
    assert len(detail["skills"]) > 0

    # 4. GET /api/v1/jobs/taxonomy/skills
    logger.info("--- 4. Testing GET /api/v1/jobs/taxonomy/skills ---")
    tax_res = await test_client.get("/api/v1/jobs/taxonomy/skills")
    skills = tax_res.json()
    logger.info(f"  Taxonomy Canonical Skills Count: {len(skills)}")
    assert tax_res.status_code == 200
    assert len(skills) > 0
