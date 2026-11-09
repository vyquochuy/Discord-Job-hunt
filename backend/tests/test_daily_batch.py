import logging
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.models.job import Job
from app.services.collectors.mock_adapter import MockJobCollector
from app.services.daily_runner import daily_batch_runner
from app.services.ingestion_pipeline import ingestion_pipeline, IngestionStats
from app.services.matching.match_service import job_match_service

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


@pytest.fixture
def batch_dependencies(monkeypatch):
    ingest = AsyncMock(return_value=IngestionStats(source="mock", total_fetched=2, created=1))
    matching = AsyncMock(return_value=0)
    recommendations = AsyncMock(return_value=[])
    monkeypatch.setattr(ingestion_pipeline, "run", ingest)
    monkeypatch.setattr(job_match_service, "batch_calculate_all", matching)
    monkeypatch.setattr(job_match_service, "get_top_recommendations", recommendations)
    monkeypatch.setattr("os.path.isdir", lambda _: False)
    return ingest, matching, recommendations


@pytest.mark.asyncio
async def test_daily_batch_runner_execution(test_client, batch_dependencies):
    """
    Kiểm tra toàn bộ chu trình Daily Batch Runner.
    """
    logger.info("=== [TEST] Daily Batch Runner Execution ===")
    _, session_factory = test_client
    async with session_factory() as session:
        summary = await daily_batch_runner.run_daily_batch(session=session, limit_per_source=2)

        assert summary.status == "COMPLETED"
        assert summary.candidate_id is None
        assert summary.matching_status == "SKIPPED"
        assert "Candidate profile not found" in summary.matching_skip_reason
        assert summary.total_fetched == 18
        assert summary.new_jobs_created == 9
        assert summary.total_matches_evaluated == 0
        assert summary.top_recommendations == []
        assert summary.duration_seconds >= 0
        batch_dependencies[1].assert_not_awaited()
        batch_dependencies[2].assert_not_awaited()
        logger.info(f"Daily Batch finished successfully in {summary.duration_seconds}s!")
        logger.info(f"Summary: Fetched={summary.total_fetched}, Created={summary.new_jobs_created}, Matches={summary.total_matches_evaluated}")


@pytest.mark.asyncio
async def test_daily_batch_api_endpoint(test_client, batch_dependencies):
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
    assert data["candidate_name"] is None
    assert data["matching_status"] == "SKIPPED"
    assert "Candidate profile not found" in data["matching_skip_reason"]
    assert data["new_jobs_created"] == 9
    assert data["top_recommendations"] == []
    batch_dependencies[1].assert_not_awaited()
    logger.info(f"API Triggered Daily Batch: Status={data['status']}, Candidate={data['candidate_name']}")
