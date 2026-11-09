"""Public catalog and stable Jobs pagination regressions (isolated SQLite)."""
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1.endpoints.jobs import router
from app.core.database import Base, get_db
from app.core.security import verify_admin_access
from app.services.ingestion_pipeline import ingestion_pipeline
from app.models.job import Job, RawJob


@pytest_asyncio.fixture
async def jobs_client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    app = FastAPI()
    app.include_router(router, prefix="/jobs")

    async def database():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_db] = database
    async with sessions() as session:
        for i in range(1, 28):
            session.add(Job(
                id=uuid.UUID(int=i),
                raw_job=RawJob(source="saramin" if i <= 13 else "custom-board",
                               source_url=f"https://example.com/{i}", content_hash=str(i)),
                title=f"Engineer {i}", normalized_title="engineer", company_name="Acme",
                normalized_company="acme", description="Python backend",
                normalized_location="hanoi" if i <= 13 else None,
                level="UNKNOWN" if i <= 13 else "LEAD", work_mode="REMOTE",
                status="ACTIVE" if i <= 25 else "EXPIRED",
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            ))
        await session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    await engine.dispose()


@pytest.mark.asyncio
async def test_public_active_catalog_and_selectable_values(jobs_client):
    response = await jobs_client.get("/jobs/filters")
    assert response.status_code == 200
    data = response.json()
    assert data["sources"] == [
        {"value": "custom-board", "label": "custom-board", "count": 12},
        {"value": "saramin", "label": "Saramin", "count": 13},
    ]
    assert {option["value"]: option["count"] for option in data["levels"]} == {"LEAD": 12, "UNKNOWN": 13}
    assert data["work_modes"] == [{"value": "REMOTE", "label": "Remote", "count": 25}]
    assert data["locations"] == [{"value": "hanoi", "label": "hanoi", "count": 13}]
    for key, param in [("sources", "source"), ("levels", "level"), ("work_modes", "work_mode"), ("locations", "location")]:
        for option in data[key]:
            selected = await jobs_client.get("/jobs", params={param: option["value"]})
            assert selected.status_code == 200
            assert selected.json()["total"] == option["count"]


@pytest.mark.asyncio
async def test_unknown_level_is_not_ignored(jobs_client):
    response = await jobs_client.get("/jobs", params={"level": "UNKNOWN"})
    assert response.status_code == 200
    assert response.json()["total"] == 13
    assert all(job["level"] == "UNKNOWN" for job in response.json()["items"])


@pytest.mark.asyncio
async def test_stable_twelve_per_page_and_boundaries(jobs_client):
    ids = []
    for page, size in [(1, 12), (2, 12), (3, 1), (4, 0)]:
        response = await jobs_client.get("/jobs", params={"page": page, "page_size": 12})
        assert response.status_code == 200
        data = response.json()
        assert (data["total"], data["page"], data["page_size"]) == (25, page, 12)
        assert len(data["items"]) == size
        ids.extend(job["id"] for job in data["items"])
    assert ids == [str(uuid.UUID(int=i)) for i in range(25, 0, -1)]
    for params in [{"page": 0}, {"page_size": 101}, {"level": "INVALID"}]:
        assert (await jobs_client.get("/jobs", params=params)).status_code == 422


@pytest.mark.asyncio
async def test_empty_catalog(jobs_client):
    async for session in jobs_client._transport.app.dependency_overrides[get_db]():
        from sqlalchemy import delete
        await session.execute(delete(Job))
        await session.commit()
    response = await jobs_client.get("/jobs/filters")
    assert response.status_code == 200
    assert response.json() == {"sources": [], "levels": [], "work_modes": [], "locations": []}


@pytest.mark.asyncio
async def test_topcv_blocked_collection_returns_safe_actionable_error(jobs_client, monkeypatch):
    from unittest.mock import AsyncMock

    jobs_client._transport.app.dependency_overrides[verify_admin_access] = lambda: True
    monkeypatch.setattr(ingestion_pipeline, "run", AsyncMock(side_effect=RuntimeError(
        "TopCV BLOCKED: access restriction; use manual JD import"
    )))
    response = await jobs_client.post("/jobs/collect", params={"source": "topcv"})
    assert response.status_code == 502
    assert response.json() == {
        "detail": "TopCV blocked automated access; import JD text manually"
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("source,message", [
    ("topcv", "internal database failure"),
    ("mock", "TopCV BLOCKED: access restriction; use manual JD import"),
])
async def test_unrelated_collection_runtime_errors_are_not_remapped(jobs_client, monkeypatch, source, message):
    from unittest.mock import AsyncMock

    jobs_client._transport.app.dependency_overrides[verify_admin_access] = lambda: True
    monkeypatch.setattr(ingestion_pipeline, "run", AsyncMock(side_effect=RuntimeError(message)))
    with pytest.raises(RuntimeError, match=message):
        await jobs_client.post("/jobs/collect", params={"source": source})
