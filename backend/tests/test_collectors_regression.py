"""Offline collector regressions: public data only, bounded pagination."""
import importlib
from unittest.mock import AsyncMock

import httpx
import pytest

from app.services.collectors.careerlink_adapter import CareerLinkJobCollector
from app.services.collectors.itnavi_adapter import ITNaviJobCollector
from app.services.collectors.growupwork_adapter import GrowUpWorkJobCollector
from app.services.collectors.topcv_adapter import TopCVJobCollector
from app.services.extraction.detail_fetcher import SUPPORTED_SOURCES


def mock_http(monkeypatch, handler):
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(handler), **kw))
    monkeypatch.setattr("asyncio.sleep", AsyncMock())


def saramin_job(id=1, **kw):
    return {"id": id, "title": "Python Engineer", "company": {"display_name": "Real Co"},
            "detail_url": f"https://saramin.vn/detail-jobs/python-{id}",
            "addresses": {"address_region_list": "Hà Nội"}, "skills_arr": ["Python"],
            "salary": {"min": "*", "max": "*", "currency": "VND"}, "status_display": "Expired", **kw}


@pytest.mark.asyncio
async def test_saramin_pagination_mapping_and_duplicates(monkeypatch):
    collector = importlib.import_module("app.services.collectors.saramin_adapter").SaraminJobCollector()
    requests = []
    def handler(request):
        requests.append(request)
        page = int(request.url.params["page"])
        assert request.url.params["job_categories_ids"] == "1"
        assert "category" not in request.url.params
        assert request.url.params["page_size"] == "20"
        assert "fields[job]" in request.url.params
        return httpx.Response(200, json={"data": [saramin_job(page if page < 3 else 2)], "meta": {"last_page": 175}})
    mock_http(monkeypatch, handler)
    rows = await collector.fetch_jobs(limit=0)
    assert len(rows) == 2 and len(requests) == 3
    assert rows[0].source == "saramin" and rows[0].raw_payload["is_expired"] is True
    parsed = await collector.parse_raw(rows[0])
    assert parsed.company_name == "Real Co" and parsed.location == "Hà Nội"
    assert parsed.min_salary is None and parsed.max_salary is None
    assert parsed.posted_at is None and parsed.expires_at is None
    assert parsed.skills_required == ["Python"]
    assert "saramin" in SUPPORTED_SOURCES


@pytest.mark.asyncio
async def test_saramin_rejects_untrusted_urls_and_stops_at_last_page(monkeypatch):
    collector = importlib.import_module("app.services.collectors.saramin_adapter").SaraminJobCollector()
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"data": [saramin_job(1, detail_url="https://evil.test/x"), saramin_job(2, detail_url="http://saramin.vn/x"), saramin_job(3)], "meta": {"last_page": 1}})
    mock_http(monkeypatch, handler)
    rows = await collector.fetch_jobs(0)
    assert [r.source_job_id for r in rows] == ["3"] and len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("collector", [ITNaviJobCollector(), GrowUpWorkJobCollector()])
@pytest.mark.parametrize("limit", [0, -1])
async def test_fullscan_nonpositive_limit_and_repeat_stop(monkeypatch, collector, limit):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, text='<div class="job-item"><h3><a href="/viec-lam/python-123">Python</a></h3></div>')
    mock_http(monkeypatch, handler)
    rows = await collector.fetch_jobs(limit)
    assert len(rows) == 1 and len(calls) == 2


@pytest.mark.asyncio
async def test_careerlink_current_markup(monkeypatch):
    mock_http(monkeypatch, lambda r: httpx.Response(200, text='''<div data-testid="job-result-row">
      <a class="JobRow__jobLink" href="/viec-lam/python/123">Python Engineer</a>
      <span class="JobRow__company">Real Company</span><span class="JobRow__location">Hà Nội</span>
      <span class="JobRow__salary">20 triệu</span><span class="JobRow__timestamp">2026-11-01</span></div>'''))
    rows = await CareerLinkJobCollector().fetch_jobs(1)
    assert len(rows) == 1
    assert rows[0].raw_payload["company"] == "Real Company"
    assert rows[0].raw_payload["salary_text"] == "20 triệu"
    assert rows[0].raw_payload["posted_at_text"] == "2026-11-01"


@pytest.mark.asyncio
@pytest.mark.parametrize("status,text", [(403, "Forbidden"), (200, "<title>Just a moment...</title>Checking your browser")])
async def test_topcv_reports_blocked(monkeypatch, status, text):
    mock_http(monkeypatch, lambda r: httpx.Response(status, text=text))
    with pytest.raises(RuntimeError, match="BLOCKED"):
        await TopCVJobCollector().fetch_jobs(1)


@pytest.mark.asyncio
async def test_careerlink_reports_robot_gate(monkeypatch):
    mock_http(monkeypatch, lambda r: httpx.Response(200, text="Xác nhận bạn không phải robot"))
    with pytest.raises(RuntimeError, match="BLOCKED"):
        await CareerLinkJobCollector().fetch_jobs(1)
