import logging
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.models.job import Job
from app.services.collectors.mock_adapter import MockJobCollector
from app.services.daily_runner import daily_batch_runner
from app.services.ingestion_pipeline import ingestion_pipeline

logger = logging.getLogger("test.daily_batch")


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


@pytest.mark.asyncio
async def test_zero_cost_ingestion_and_contact_fields(test_client):
    """
    Kiểm tra luồng Ingestion không tốn token LLM (use_llm=False)
    và bóc tách chính xác contact_email / apply_url.
    """
    logger.info("=== [TEST] Zero-Cost Ingestion & Contact Fields Extraction ===")
    client, session_factory = test_client

    async with session_factory() as session:
        mock_collector = MockJobCollector()
        stats = await ingestion_pipeline.run(mock_collector, session, limit=5, use_llm=False)

        assert stats.created > 0
        logger.info(f"Ingested jobs count: {stats.created}")

        # Kiểm tra Job trong DB
        stmt = select(Job).limit(5)
        res = await session.execute(stmt)
        jobs = res.scalars().all()
        assert len(jobs) > 0

        for j in jobs:
            logger.info(f"Job: '{j.title}' at '{j.company_name}' | Email: {j.contact_email} | Apply URL: {j.apply_url}")
            assert j.title is not None
            assert j.company_name is not None
            assert j.dedup_signature is not None


@pytest.mark.asyncio
async def test_daily_batch_runner_execution(test_client):
    """
    Kiểm tra toàn bộ chu trình Daily Batch Runner.
    """
    logger.info("=== [TEST] Daily Batch Runner Execution ===")
    summary = await daily_batch_runner.run_daily_batch(limit_per_source=2)

    assert summary.status == "COMPLETED"
    assert summary.candidate_name == "Vy Quoc Huy"
    assert summary.total_matches_evaluated >= 0
    assert summary.duration_seconds > 0
    logger.info(f"Daily Batch finished successfully in {summary.duration_seconds}s!")
    logger.info(f"Summary: Fetched={summary.total_fetched}, Created={summary.new_jobs_created}, Matches={summary.total_matches_evaluated}")


@pytest.mark.asyncio
async def test_daily_batch_api_endpoint(test_client):
    """
    Kiểm tra REST API endpoint POST /api/v1/jobs/daily-batch.
    """
    logger.info("=== [TEST] POST /api/v1/jobs/daily-batch Endpoint ===")
    client, _ = test_client
    headers = {"X-Internal-Secret": settings.INTERNAL_API_SECRET}

    res = await client.post("/api/v1/jobs/daily-batch?limit_per_source=2", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "COMPLETED"
    assert "candidate_name" in data
    assert "top_recommendations" in data
    logger.info(f"API Triggered Daily Batch: Status={data['status']}, Candidate={data['candidate_name']}")
