import pytest
import httpx
from app.services.collectors.saramin_adapter import SaraminJobCollector
from .test_collectors_regression import mock_http, saramin_job


@pytest.mark.asyncio
async def test_observed_published_dates_and_masked_salary(monkeypatch):
    job = saramin_job(published={"date": "03-11-2026", "datetime": "00:00:00 03-11-2026"},
                      status_display="Open", salary={"min": "6******", "max": "7******", "min_filter": 6000000,
                      "max_filter": 7000000, "currency": "VND", "is_negotiable": "0"})
    mock_http(monkeypatch, lambda r: httpx.Response(200, json={"data": [job], "meta": {"last_page": 1}}))
    collector = SaraminJobCollector()
    rows = await collector.fetch_jobs(1)
    parsed = await collector.parse_raw(rows[0])
    assert parsed.posted_at.day == 3 and parsed.posted_at.month == 11
    assert parsed.salary_currency == "VND"
    assert parsed.min_salary is None and parsed.max_salary is None
    assert rows[0].raw_payload["is_expired"] is False
