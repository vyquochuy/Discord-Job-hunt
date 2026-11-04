"""
Phase 2.8 — Full Unexpired Scanning & Expiry Detection Test Suite

Kiểm tra:
1. Trích xuất hạn nộp (validThrough / deadline DOM / "Hạn nộp hồ sơ: dd/mm/yyyy").
2. Phát hiện tin đã hết hạn (marker text + ngày hết hạn đã qua).
3. Richer-record merge lưu expires_iso / is_expired vào payload.
4. Adapter parse_raw map expires_iso -> JobExtractedData.expires_at.
5. VietnamWorks API: expiredDate (epoch ms) -> expires_iso + is_expired.
6. Pipeline: job quá hạn lưu với status EXPIRED, future expiry giữ ACTIVE.
7. expire_outdated_jobs(): chuyển ACTIVE quá hạn -> EXPIRED.
8. full_scan=True: limit=0 tới collector và không dừng sớm vì unchanged streak.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List

import pytest
import pytest_asyncio
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.models.job import Job, JobStatusEnum, RawJob, RawJobStatusEnum
from app.schemas.job import JobExtractedData
from app.services.collectors.base import BaseJobCollector, RawJobData
from app.services.collectors.vietnamworks_adapter import VietnamWorksJobCollector
from app.services.extraction.detail_fetcher import (
    JobDetailFetcher,
    JobDetailResult,
    check_is_job_expired,
    extract_deadline_from_dom,
    merge_detail_into_payload,
    parse_posted_datetime,
)
from app.services.ingestion_pipeline import ingestion_pipeline

logger = logging.getLogger("test.expiry_full_scan")


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest_asyncio.fixture
async def async_db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture(autouse=True)
def no_sleep_in_backoff(monkeypatch):
    """Backoff sleep -> no-op để test chạy nhanh."""
    import importlib
    df_module = importlib.import_module("app.services.extraction.detail_fetcher")

    async def _instant_sleep(delay):
        return None

    monkeypatch.setattr(df_module.asyncio, "sleep", _instant_sleep)


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


# ==============================================================================
# 1. Deadline / Expiry detection
# ==============================================================================

class TestDeadlineExtraction:
    def test_vietnamese_deadline_regex(self):
        soup = _soup("<html><body><div>Hạn nộp hồ sơ: 30/11/2026</div></body></html>")
        dt = extract_deadline_from_dom(soup)
        assert dt is not None
        assert (dt.year, dt.month, dt.day) == (2026, 11, 30)

    def test_topcv_deadline_class(self):
        soup = _soup(
            '<html><body><div class="job-detail__info--deadline">Hạn nộp: 15/12/2026</div></body></html>'
        )
        dt = extract_deadline_from_dom(soup)
        assert dt is not None and dt.day == 15 and dt.month == 12

    def test_no_deadline_returns_none(self):
        soup = _soup("<html><body><main>We build things. No deadline here.</main></body></html>")
        assert extract_deadline_from_dom(soup) is None

    def test_expired_marker_detected(self):
        soup = _soup("<html><body><div>Tin tuyển dụng này đã hết hạn</div></body></html>")
        assert check_is_job_expired(soup) is True

    def test_expired_english_marker_detected(self):
        soup = _soup("<html><body><div>This job is no longer available</div></body></html>")
        assert check_is_job_expired(soup) is True

    def test_active_job_not_flagged_expired(self):
        soup = _soup(
            "<html><body><main>"
            + ("We are hiring backend engineers to build distributed systems. " * 20)
            + "</main></body></html>"
        )
        assert check_is_job_expired(soup) is False


# ==============================================================================
# 2. JSON-LD validThrough -> expires_at
# ==============================================================================

def _jobposting_html(job_posting: dict, fallback_body: str = "Fallback body. ") -> str:
    """Dựng trang chi tiết có JSON-LD JobPosting hợp lệ (tránh lỗi escape thủ công)."""
    import json as _json

    ld = _json.dumps(job_posting, ensure_ascii=False)
    return (
        "<html><head><script type=\"application/ld+json\">"
        + ld
        + "</script></head><body><main>"
        + (fallback_body * 100)
        + "</main></body></html>"
    )


class TestJsonLdValidThrough:
    @pytest.mark.asyncio
    async def test_valid_through_extracted_from_jsonld(self, monkeypatch):
        fetcher = JobDetailFetcher()
        doc = _fake_doc(
            html=_jobposting_html(
                {
                    "@type": "JobPosting",
                    "datePosted": "2026-10-01T00:00:00Z",
                    "validThrough": "2099-12-31T23:59:59Z",
                    "description": "<p>" + ("Detailed JD body content. " * 40) + "</p>",
                }
            )
        )
        _patch_url_fetcher(monkeypatch, _async_return(doc))

        result = await fetcher.fetch_detail("itviec", "https://itviec.com/it-jobs/x")
        assert result.status == "OK"
        assert result.expires_at is not None
        assert result.expires_at.year == 2099
        assert result.is_expired is False

    @pytest.mark.asyncio
    async def test_past_valid_through_marks_expired(self, monkeypatch):
        fetcher = JobDetailFetcher()
        doc = _fake_doc(
            html=_jobposting_html(
                {
                    "@type": "JobPosting",
                    "validThrough": "2020-01-01T00:00:00Z",
                    "description": "<p>" + ("Old JD body content. " * 40) + "</p>",
                }
            )
        )
        _patch_url_fetcher(monkeypatch, _async_return(doc))

        result = await fetcher.fetch_detail("topcv", "https://www.topcv.vn/viec-lam/x/1.html")
        assert result.status == "OK"
        assert result.is_expired is True
        assert result.expires_at.year == 2020


# ==============================================================================
# 3. Merge helper
# ==============================================================================

class TestMergeExpiry:
    def test_merge_writes_expires_and_flag(self):
        payload = {"title": "Backend Dev", "description": "short"}
        future = datetime.now(timezone.utc) + timedelta(days=10)
        result = JobDetailResult(
            source="itviec",
            url="https://x",
            status="OK",
            description="Full JD. " * 50,
            expires_at=future,
            is_expired=False,
            method="jsonld",
        )
        merged = merge_detail_into_payload(payload, result)
        assert merged["expires_iso"].startswith(future.date().isoformat())
        assert merged["detail_meta"]["expires_at"] is not None
        assert merged["detail_meta"]["is_expired"] is False
        assert "is_expired" not in merged

    def test_merge_marks_expired_payload(self):
        payload = {"title": "Backend Dev"}
        result = JobDetailResult(
            source="topcv",
            url="https://x",
            status="OK",
            description="Full JD. " * 50,
            is_expired=True,
            method="site_dom",
        )
        merged = merge_detail_into_payload(payload, result)
        assert merged["is_expired"] is True


# ==============================================================================
# 4. VietnamWorks API: expiredDate epoch -> expires_iso / is_expired
# ==============================================================================

class _FakeResponse:
    def __init__(self, payload):
        self.status_code = 200
        self._payload = payload

    def json(self):
        return self._payload


class _FakeAsyncClient:
    """Giả lập httpx.AsyncClient chỉ cho POST search API."""

    def __init__(self, pages: List[list], *args, **kwargs):
        self._pages = pages
        self._call = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, headers=None, json=None):
        page = (json or {}).get("page", 0)
        data = self._pages[page] if page < len(self._pages) else []
        return _FakeResponse({"data": data})

    async def get(self, *args, **kwargs):  # pragma: no cover - không dùng
        return _FakeResponse({"data": []})


class TestVietnamWorksExpiry:
    @pytest.mark.asyncio
    async def test_expired_date_parsed_and_flagged(self, monkeypatch):
        import importlib
        vw_module = importlib.import_module("app.services.collectors.vietnamworks_adapter")

        future_ms = int((datetime.now(timezone.utc) + timedelta(days=20)).timestamp() * 1000)
        past_ms = int((datetime.now(timezone.utc) - timedelta(days=20)).timestamp() * 1000)
        posted_ms = int((datetime.now(timezone.utc) - timedelta(days=2)).timestamp() * 1000)

        page0 = [
            {
                "jobId": 111,
                "jobTitle": "Backend Engineer",
                "jobUrl": "/viec-lam/backend-engineer/111",
                "companyName": "ACME",
                "workingLocations": [{"cityNameVI": "Hồ Chí Minh"}],
                "salaryMin": 1000,
                "salaryMax": 2000,
                "salaryCurrency": "USD",
                "skills": [{"skillName": "Python"}],
                "jobDescription": "Build APIs.",
                "approvedOn": posted_ms,
                "expiredDate": future_ms,
            },
            {
                "jobId": 222,
                "jobTitle": "Legacy Dev",
                "jobUrl": "/viec-lam/legacy-dev/222",
                "companyName": "OldCorp",
                "workingLocations": [],
                "jobDescription": "Maintain COBOL.",
                "expiredDate": past_ms,
            },
        ]

        monkeypatch.setattr(vw_module.httpx, "AsyncClient", lambda *a, **k: _FakeAsyncClient([page0]))

        collector = VietnamWorksJobCollector()
        raws = await collector.fetch_jobs(limit=0)

        assert len(raws) == 2
        first = raws[0].raw_payload
        assert first["expires_iso"] is not None
        assert first["is_expired"] is False
        assert first["posted_iso"] is not None

        second = raws[1].raw_payload
        assert second["is_expired"] is True

        extracted = await collector.parse_raw(raws[0])
        assert extracted.expires_at is not None
        assert extracted.expires_at > datetime.now(timezone.utc)


# ==============================================================================
# 5. Pipeline: EXPIRED status + expire_outdated_jobs + full_scan
# ==============================================================================

class _StubCollector(BaseJobCollector):
    """Collector giả lập nguồn VN (itviec) với expiry điều khiển được."""

    def __init__(self, count: int = 1, expires_at=None, is_expired: bool = False):
        self.count = count
        self.expires_at = expires_at
        self.is_expired = is_expired
        self.last_limit = None

    @property
    def source_name(self) -> str:
        return "itviec"

    async def fetch_jobs(self, limit: int = 20) -> List[RawJobData]:
        self.last_limit = limit
        total = self.count if limit <= 0 else min(self.count, limit)
        results = []
        for i in range(total):
            title = f"Backend Engineer Level {i}"
            url = f"https://itviec.com/it-jobs/backend-engineer-{i}"
            payload = {
                "title": title,
                "company": f"ACME {i}",
                "location": "Ho Chi Minh City",
                "url": url,
                "skills": ["Python"],
                "expires_iso": self.expires_at.isoformat() if self.expires_at else None,
                "is_expired": self.is_expired,
            }
            results.append(
                RawJobData(
                    source=self.source_name,
                    source_url=url,
                    source_job_id=f"job-{i}",
                    raw_payload=payload,
                    raw_html=f"<div>{title}</div>",
                    content_hash=BaseJobCollector.compute_content_hash(f"{title}|ACME {i}|{url}"),
                )
            )
        return results

    async def parse_raw(self, raw: RawJobData) -> JobExtractedData:
        payload = raw.raw_payload or {}
        return JobExtractedData(
            title=payload["title"],
            company_name=payload["company"],
            location=payload.get("location"),
            description=str(payload.get("description") or "Backend job description. " * 30),
            skills_required=payload.get("skills", []),
            expires_at=parse_posted_datetime(payload.get("expires_iso")),
        )


class TestPipelineExpiry:
    @pytest.mark.asyncio
    async def test_past_expiry_stored_as_expired(self, async_db_session, monkeypatch):
        async def no_detail(*args, **kwargs):  # pragma: no cover
            raise AssertionError("detail fetch không được gọi")

        monkeypatch.setattr(ingestion_pipeline, "_noop", None, raising=False)
        from app.services.extraction.detail_fetcher import detail_fetcher
        monkeypatch.setattr(detail_fetcher, "fetch_detail", no_detail)

        past = datetime.now(timezone.utc) - timedelta(days=3)
        collector = _StubCollector(count=1, expires_at=past)
        stats = await ingestion_pipeline.run(collector, async_db_session, limit=5, fetch_details=False)

        assert stats.created == 1
        assert stats.expired_marked == 1

        job = (await async_db_session.execute(select(Job))).scalars().first()
        assert job.status == JobStatusEnum.EXPIRED
        assert job.expires_at is not None

    @pytest.mark.asyncio
    async def test_future_expiry_stored_as_active(self, async_db_session):
        future = datetime.now(timezone.utc) + timedelta(days=15)
        collector = _StubCollector(count=1, expires_at=future)
        stats = await ingestion_pipeline.run(collector, async_db_session, limit=5, fetch_details=False)

        assert stats.created == 1
        assert stats.expired_marked == 0

        job = (await async_db_session.execute(select(Job))).scalars().first()
        assert job.status == JobStatusEnum.ACTIVE
        assert job.expires_at is not None

    @pytest.mark.asyncio
    async def test_payload_is_expired_flag_overrides(self, async_db_session):
        future = datetime.now(timezone.utc) + timedelta(days=15)
        collector = _StubCollector(count=1, expires_at=future, is_expired=True)
        stats = await ingestion_pipeline.run(collector, async_db_session, limit=5, fetch_details=False)

        job = (await async_db_session.execute(select(Job))).scalars().first()
        assert job.status == JobStatusEnum.EXPIRED
        assert stats.expired_marked == 1

    @pytest.mark.asyncio
    async def test_expire_outdated_jobs_marks_active_rows(self, async_db_session):
        past = datetime.now(timezone.utc) - timedelta(days=1)
        future = datetime.now(timezone.utc) + timedelta(days=30)

        raw = RawJob(
            source="itviec",
            source_url="https://itviec.com/it-jobs/seed",
            content_hash="c" * 64,
            fetch_status=RawJobStatusEnum.PARSED.value,
        )
        raw2 = RawJob(
            source="itviec",
            source_url="https://itviec.com/it-jobs/seed-2",
            content_hash="d" * 64,
            fetch_status=RawJobStatusEnum.PARSED.value,
        )
        async_db_session.add_all([raw, raw2])
        await async_db_session.flush()

        expired_job = Job(
            raw_job_id=raw.id,
            title="Old Job",
            normalized_title="old job",
            company_name="OldCorp",
            normalized_company="oldcorp",
            description="old",
            status=JobStatusEnum.ACTIVE,
            expires_at=past,
        )
        still_active = Job(
            raw_job_id=raw2.id,
            title="Fresh Job",
            normalized_title="fresh job",
            company_name="NewCorp",
            normalized_company="newcorp",
            description="fresh",
            status=JobStatusEnum.ACTIVE,
            expires_at=future,
        )
        async_db_session.add_all([expired_job, still_active])
        await async_db_session.commit()

        marked = await ingestion_pipeline.expire_outdated_jobs(async_db_session)
        assert marked == 1

        await async_db_session.refresh(expired_job)
        await async_db_session.refresh(still_active)
        assert expired_job.status == JobStatusEnum.EXPIRED
        assert still_active.status == JobStatusEnum.ACTIVE


class TestFullScanMode:
    @pytest.mark.asyncio
    async def test_full_scan_passes_zero_limit_to_collector(self, async_db_session):
        collector = _StubCollector(count=2)
        await ingestion_pipeline.run(collector, async_db_session, limit=1, full_scan=True, fetch_details=False)
        assert collector.last_limit == 0

    @pytest.mark.asyncio
    async def test_incremental_keeps_limit(self, async_db_session):
        collector = _StubCollector(count=2)
        await ingestion_pipeline.run(collector, async_db_session, limit=7, fetch_details=False)
        assert collector.last_limit == 7

    @pytest.mark.asyncio
    async def test_full_scan_does_not_stop_at_unchanged_streak(self, async_db_session):
        """35 tin đã có sẵn: incremental dừng ở 30, full_scan xử lý hết 35."""
        collector = _StubCollector(count=35)
        raws = await collector.fetch_jobs(limit=0)

        # Seed toàn bộ raw jobs với content_hash khớp -> pipeline coi là unchanged
        for raw in raws:
            async_db_session.add(
                RawJob(
                    source=raw.source,
                    source_url=raw.source_url,
                    source_job_id=raw.source_job_id,
                    content_hash=raw.content_hash,
                    raw_payload=raw.raw_payload,
                    fetch_status=RawJobStatusEnum.PARSED.value,
                )
            )
        await async_db_session.commit()

        incremental = await ingestion_pipeline.run(
            _StubCollector(count=35), async_db_session, limit=0, fetch_details=False
        )
        assert incremental.unchanged == 30

        full = await ingestion_pipeline.run(
            _StubCollector(count=35), async_db_session, limit=0, full_scan=True, fetch_details=False
        )
        assert full.unchanged == 35


# ==============================================================================
# Helper: URLFetcher mocking
# ==============================================================================

def _fake_doc(html: str):
    from app.services.extraction.url_fetcher import FetchedDocument

    soup = BeautifulSoup(html, "html.parser")
    json_ld = None
    if "application/ld+json" in html:
        import json as _json
        for s in soup.find_all("script", type="application/ld+json"):
            try:
                json_ld = _json.loads(s.string or "")
                break
            except Exception:
                continue
    for tag in soup(["script", "style"]):
        tag.decompose()
    return FetchedDocument(
        url="https://stub",
        final_url="https://stub",
        status_code=200,
        content_type="text/html",
        html=html,
        title=soup.title.get_text(strip=True) if soup.title else None,
        meta_description=None,
        og_title=None,
        og_description=None,
        json_ld=json_ld,
        clean_text=soup.get_text("\n", strip=True),
        fetch_method="httpx",
    )


def _patch_url_fetcher(monkeypatch, fetch_callable):
    import importlib
    uf_module = importlib.import_module("app.services.extraction.url_fetcher")
    monkeypatch.setattr(uf_module.url_fetcher, "fetch", fetch_callable)


def _async_return(value):
    async def _inner(*args, **kwargs):
        return value

    return _inner
