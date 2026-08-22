import logging
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.services.collectors.mock_adapter import MockJobCollector
from app.services.ingestion_pipeline import ingestion_pipeline

logger = logging.getLogger("test.match_api")


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
async def test_match_api_complete_lifecycle(test_client):
    """
    Kiểm thử toàn bộ vòng đời của API Phân tích độ phù hợp (Job Intelligence):
    1. Đồng bộ Candidate Profile
    2. Thu thập Jobs mẫu vào DB
    3. Tính toán Match đơn lẻ (POST /api/v1/matches/calculate/{job_id})
    4. Lấy chi tiết Match (GET /api/v1/matches/{job_id})
    5. Lấy danh sách Matches (GET /api/v1/matches)
    6. Lấy danh sách Top Recommendations (GET /api/v1/matches/recommendations/top)
    7. Tính toán hàng loạt (POST /api/v1/matches/calculate-all)
    """
    client, session_factory = test_client
    headers = {"X-Internal-Secret": settings.INTERNAL_API_SECRET}

    logger.info("=== [TEST] Match API Complete Lifecycle ===")

    # Step 1: Đồng bộ profile
    sync_res = await client.post("/api/v1/profile/sync", headers=headers)
    assert sync_res.status_code == 200

    # Step 2: Thu thập Jobs mẫu
    async with session_factory() as session:
        mock_collector = MockJobCollector()
        stats = await ingestion_pipeline.run(mock_collector, session, limit=5)
        logger.info(f"Ingested mock jobs: Created={stats.created}")

    # Lấy danh sách jobs từ DB
    jobs_res = await client.get("/api/v1/jobs", headers=headers)
    assert jobs_res.status_code == 200
    jobs = jobs_res.json()["items"]
    assert len(jobs) > 0
    target_job_id = jobs[0]["id"]
    logger.info(f"Target Job for Match: ID={target_job_id}, Title='{jobs[0]['title']}'")

    # Step 3: Tính toán Match đơn lẻ
    calc_res = await client.post(
        f"/api/v1/matches/calculate/{target_job_id}?force_refresh=true", headers=headers
    )
    assert calc_res.status_code == 200
    match_detail = calc_res.json()
    logger.info(
        f"Match Detail: Score={match_detail['score']}, Eligibility={match_detail['eligibility']}, "
        f"Recommendation={match_detail['recommendation']}"
    )

    assert 0.0 <= match_detail["score"] <= 100.0
    assert match_detail["eligibility"] in ["ELIGIBLE", "BLOCKED", "UNCERTAIN"]
    assert match_detail["recommendation"] in [
        "STRONG_MATCH", "GOOD_MATCH", "WEAK_MATCH", "POOR_MATCH", "DO_NOT_APPLY", "REVIEW_REQUIRED"
    ]
    assert len(match_detail["signals"]) == 7
    assert len(match_detail["hard_filter_results"]) == 4
    assert match_detail["explanation"] is not None
    assert match_detail["candidate_snapshot"] is not None
    assert match_detail["job_snapshot"] is not None

    # Step 4: Lấy chi tiết Match (GET /api/v1/matches/{job_id})
    get_res = await client.get(f"/api/v1/matches/{target_job_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == match_detail["id"]

    # Step 5: Lấy danh sách Matches (GET /api/v1/matches)
    list_res = await client.get("/api/v1/matches?page=1&page_size=10", headers=headers)
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert len(list_data["items"]) >= 1

    # Step 6: Tính toán hàng loạt (POST /api/v1/matches/calculate-all)
    batch_res = await client.post("/api/v1/matches/calculate-all", headers=headers)
    assert batch_res.status_code == 200
    batch_data = batch_res.json()
    logger.info(f"Batch calculate response: {batch_data}")
    assert batch_data["total_jobs"] >= len(jobs)

    # Step 7: Lấy Top Recommendations (GET /api/v1/matches/recommendations/top)
    top_res = await client.get(
        "/api/v1/matches/recommendations/top?limit=5&min_score=0.0", headers=headers
    )
    assert top_res.status_code == 200
    top_items = top_res.json()
    logger.info(f"Top recommendations count: {len(top_items)}")
    assert len(top_items) > 0
    # Đảm bảo không có công việc nào bị BLOCKED lọt vào top recommendations
    for item in top_items:
        assert item["eligibility"] != "BLOCKED"
