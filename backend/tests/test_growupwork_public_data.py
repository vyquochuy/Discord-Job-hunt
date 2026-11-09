import json
import httpx
import pytest
from app.services.collectors.growupwork_adapter import GrowUpWorkJobCollector
from .test_collectors_regression import mock_http


@pytest.mark.asyncio
async def test_embedded_public_vue_jobs(monkeypatch):
    job = {"id": 5821, "job_id": "abc123", "position": "AI/Robotics Engineer",
           "client_job_category_id": 2, "client": {"company_name": "Real Company"},
           "place_of_work": "HCM", "job_description": "Build robots", "release_date": "2026-11-01", "salary": "70,000,000"}
    attrs = json.dumps({"data": [job], "last_page": 1})
    cats = json.dumps([{"id": 2, "name": "IT Engineer"}])
    mock_http(monkeypatch, lambda r: httpx.Response(200, text=f"<search-job-component :search_jobs='{attrs}' :all_job_categories='{cats}'></search-job-component>"))
    rows = await GrowUpWorkJobCollector().fetch_jobs(0)
    assert len(rows) == 1 and rows[0].source_job_id == "abc123"
    assert rows[0].raw_payload["company"] == "Real Company"
    assert rows[0].source_url == "https://growupwork.com/viec-lam/it-engineer/ai-robotics-engineer-abc123"
    parsed = await GrowUpWorkJobCollector().parse_raw(rows[0])
    assert "Build robots" in parsed.description and parsed.posted_at.day == 1


@pytest.mark.asyncio
async def test_empty_response_never_invents_jobs(monkeypatch):
    calls = []
    def handler(r):
        calls.append(r)
        return httpx.Response(200, text="<html>No listings</html>")
    mock_http(monkeypatch, handler)
    assert await GrowUpWorkJobCollector().fetch_jobs(0) == []
    assert len(calls) == 1
