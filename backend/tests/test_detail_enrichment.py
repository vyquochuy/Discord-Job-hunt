"""
Phase 2.7 — Detail Page Enrichment Test Suite

Kiểm tra thành phần mới của Ingestion Hardening:
1. JobDetailFetcher: JSON-LD JobPosting extraction, challenge/login detection
   (KHÔNG tự bypass), quality validation, retry với terminal HTTP statuses.
2. merge/note helpers: richer-record merge (description dài hơn thắng,
   skills union lossless, posted date tin cậy).
3. parse_posted_datetime: ISO 8601, epoch, relative text VN/EN.
4. Adapter parse_raw: ưu tiên detail-enriched description + posted date.
5. Pipeline integration (SQLite in-memory): detail enrichment tăng metrics,
   description đầy đủ được lưu, failure vẫn tiếp tục với listing data.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.models.job import Job, RawJob
from app.schemas.job import JobExtractedData
from app.services.collectors.base import BaseJobCollector, RawJobData
from app.services.extraction.detail_fetcher import (
    JobDetailFetcher,
    JobDetailResult,
    clean_html_to_text,
    is_challenge_page,
    is_login_gate,
    merge_detail_into_payload,
    note_detail_failure,
    parse_posted_datetime,
)
from app.services.extraction.detail_fetcher import detail_fetcher
from app.services.ingestion_pipeline import ingestion_pipeline
from app.services.collectors.itviec_adapter import ITViecJobCollector
from app.services.collectors.topcv_adapter import TopCVJobCollector

logger = logging.getLogger("test.detail_enrichment")


@pytest.fixture(autouse=True)
def no_sleep_in_backoff(monkeypatch):
    """Đưa backoff sleep về no-op để test suite chạy không bị delay."""
    from app.services.extraction import detail_fetcher as df_module
    async def _instant_sleep(delay):
        return None
    monkeypatch.setattr(df_module.asyncio, "sleep", _instant_sleep)


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


# ==============================================================================
# 1. parse_posted_datetime
# ==============================================================================

class TestPostedDateParser:
    def test_iso_string(self):
        dt = parse_posted_datetime("2026-10-30T09:00:00+07:00")
        assert dt is not None
        assert dt.year == 2026 and dt.month == 10 and dt.day == 30
        assert dt.tzinfo is not None

    def test_iso_z_suffix(self):
        dt = parse_posted_datetime("2026-10-30T09:00:00Z")
        assert dt is not None and dt.tzinfo is not None

    def test_epoch_millis(self):
        dt = parse_posted_datetime(1730000000000)
        assert dt is not None
        assert dt.year >= 2024

    def test_relative_text_posted_prefix(self):
        before = datetime.now(timezone.utc) - timedelta(days=4)
        after_candidate = datetime.now(timezone.utc) - timedelta(days=2)
        dt = parse_posted_datetime("Posted 3 days ago")
        assert dt is not None
        assert before < dt < after_candidate

    def test_relative_text_vietnamese(self):
        dt = parse_posted_datetime("5 ngày trước")
        assert dt is not None
        assert (datetime.now(timezone.utc) - dt).days >= 4

    def test_yesterday(self):
        dt = parse_posted_datetime("hôm qua")
        assert dt is not None
        assert (datetime.now(timezone.utc) - dt).days == 1

    def test_invalid_returns_none(self):
        assert parse_posted_datetime("Unknowable Gobbledygook") is None
        assert parse_posted_datetime("") is None
        assert parse_posted_datetime(None) is None


# ==============================================================================
# 2. Challenge / Login detection (chỉ detect, không bypass)
# ==============================================================================

class TestSecurityDetection:
    def test_cloudflare_challenge_detected(self):
        soup = clean_soup(
            """
            <html><head><title>Just a moment...</title></head>
            <body><div id="challenge-error-text">Enable JavaScript and cookies to continue</div></body>
            </html>
            """
        )
        assert is_challenge_page(soup) is not None

    def test_normal_job_page_not_challenge(self):
        soup = clean_soup(
            """
            <html><head><title>Backend Engineer - ACME Corp</title></head>
            <body><main><h1>Job responsibilities include API design and cloud.</h1></main></body>
            </html>
            """
        )
        assert is_challenge_page(soup) is None

    def test_login_gate_detected(self):
        soup = clean_soup(
            """
            <html><head><title>Đăng nhập | JobBoard</title></head>
            <body><div>Hãy đăng nhập để xem chi tiết tin tuyển dụng này</div></body>
            </html>
            """
        )
        assert is_login_gate(soup) is not None

    def test_login_marker_in_rich_jd_not_flagged(self):
        # False-positive protection: JD dài không bị misclass chỉ vì nhắc 'sign in'
        soup = clean_soup(
            """
            <html><head><title>Senior Backend Engineer</title></head>
            <body><main>
            """ + ("We build cloud services. " * 80) + """
            Candidates must sign in to the internal CI system after onboarding.
            </main></body></html>
            """
        )
        assert is_login_gate(soup) is None


def clean_soup(html: str):
    from bs4 import BeautifulSoup
    return BeautifulSoup(html, "html.parser")


# ==============================================================================
# 3. Merge helpers (richer-record semantics)
# ==============================================================================

class TestMergeHelpers:
    def test_longer_detail_wins(self):
        payload = {"title": "Backend Dev", "description": "short listing desc"}
        result = JobDetailResult(source="itviec", url="https://x", status="OK",
                                 description="FULL detailed job description " * 20, method="jsonld")
        merged = merge_detail_into_payload(payload, result)
        assert merged["description"].startswith("FULL detailed job description")
        assert merged["detail_meta"]["method"] == "jsonld"
        assert len(merged["detail_meta"]["description_hash"]) == 64

    def test_shorter_detail_does_not_downgrade(self):
        full = "Very complete JD published on the detail page. " * 30
        payload = {"title": "Backend Dev", "description": full}
        result = JobDetailResult(source="itviec", url="https://x", status="OK",
                                 description="tiny", method="page_text")
        merged = merge_detail_into_payload(payload, result)
        assert merged["description"] == full

    def test_skills_union_lossless_no_duplicates(self):
        payload = {"skills": ["Python", "FastAPI"]}
        result = JobDetailResult(source="topcv", url="https://x", status="OK",
                                 description="JD " * 150, skills=["python", "Docker", "Kubernetes"])
        merged = merge_detail_into_payload(payload, result)
        lowered = [s.lower() for s in merged["skills"]]
        assert lowered.count("python") == 1
        assert "Docker" in merged["skills"] and "Kubernetes" in merged["skills"]
        assert "FastAPI" in merged["skills"]

    def test_posted_iso_not_overwritten(self):
        payload = {"posted_iso": "2026-01-01T00:00:00+00:00"}
        result = JobDetailResult(source="itviec", url="https://x", status="OK",
                                 description="JD " * 150,
                                 posted_at=datetime(2026, 10, 30, tzinfo=timezone.utc))
        merged = merge_detail_into_payload(payload, result)
        assert merged["posted_iso"] == "2026-01-01T00:00:00+00:00"

    def test_note_failure_keeps_listing_payload(self):
        payload = {"title": "Backend Dev", "description": "listing desc", "skills": ["Python"]}
        result = JobDetailResult(source="topcv", url="https://x", status="BLOCKED",
                                 error="WAF_CHALLENGE:CHALLENGE_TITLE", attempts=2)
        noted = note_detail_failure(payload, result)
        assert noted["description"] == "listing desc"
        assert noted["detail_meta"]["status"] == "BLOCKED"
        assert noted["detail_meta"]["error"] == "WAF_CHALLENGE:CHALLENGE_TITLE"


# ==============================================================================
# 4. JobDetailFetcher.fetch_detail (mock URLFetcher responses)
# ==============================================================================

class TestDetailFetcher:
    @pytest.mark.asyncio
    async def test_jsonld_extraction(self, monkeypatch):
        fetcher = JobDetailFetcher()
        jd_html = """<div><h2>Your role</h2><p>""" + ("Design scalable services. " * 40) + """</p></div>"""
        doc = _fake_doc(html=f"""
            <html><head><script type="application/ld+json">{{
                "@type": "JobPosting",
                "datePosted": "2026-10-30T09:00:00+07:00",
                "employmentType": "FULL_TIME",
                "description": "<p>{'Complete JD description content. ' * 60}</p>",
                "skills": ["Python", "Django", "PostgreSQL"]
            }}</script></head><body>{jd_html}</body></html>
        """)
        _patch_url_fetcher(monkeypatch, _async_return(doc))

        result = await fetcher.fetch_detail("itviec", "https://itviec.com/it-jobs/test")
        assert result.status == "OK"
        assert result.method == "jsonld"
        assert "Complete JD description content." in result.description
        assert result.employment_type == "FULL_TIME"
        assert result.posted_at is not None and result.posted_at.year == 2026
        assert "Python" in result.skills

    @pytest.mark.asyncio
    async def test_http_403_is_terminal_blocked_no_retry(self, monkeypatch):
        fetcher = JobDetailFetcher()
        attempts = []

        class TerminalDoc:
            pass

        async def fail_fetch(url, timeout=10.0):
            attempts.append(url)
            return _failed_doc(error="HTTP_403", status_code=403)

        _patch_url_fetcher(monkeypatch, fail_fetch)
        collector_result = await fetcher.fetch_detail("topcv", "https://www.topcv.vn/viec-lam/x", max_attempts=3)
        assert collector_result.status == "BLOCKED"
        assert len(attempts) == 1  # terminal -> KHÔNG retry (Invariant 19/22)

    @pytest.mark.asyncio
    async def test_retry_then_success_on_transient_error(self, monkeypatch):
        fetcher = JobDetailFetcher()
        calls = {"n": 0}
        good_doc = _fake_doc(html="<html><body><main>" + "Real JD body text. " * 200 + "</main></body></html>")

        async def flaky_fetch(url, timeout=10.0):
            calls["n"] += 1
            if calls["n"] < 2:
                return _failed_doc(error="TIMEOUT", status_code=0)
            return good_doc

        _patch_url_fetcher(monkeypatch, flaky_fetch)
        result = await fetcher.fetch_detail("careerlink", "https://www.careerlink.vn/job/1", max_attempts=2)
        assert result.status == "OK"
        assert calls["n"] == 2

    @pytest.mark.asyncio
    async def test_insufficient_content_incomplete(self, monkeypatch):
        fetcher = JobDetailFetcher()
        thin_doc = _fake_doc(html="<html><body><main>Contact us</main></body></html>", clean_text="Contact us")
        _patch_url_fetcher(monkeypatch, _async_return(thin_doc))
        result = await fetcher.fetch_detail("itviec", "https://itviec.com/it-jobs/thin")
        assert result.status == "INCOMPLETE"
        assert result.error == "INSUFFICIENT_CONTENT"

    @pytest.mark.asyncio
    async def test_waf_challenge_marked_blocked(self, monkeypatch):
        fetcher = JobDetailFetcher()
        cf_doc = _fake_doc(html="""
            <html><head><title>Attention Required! | Cloudflare</title></head>
            <body><div id="challenge-form">Verify you are human</div></body></html>
        """)
        _patch_url_fetcher(monkeypatch, _async_return(cf_doc))
        result = await fetcher.fetch_detail("topcv", "https://www.topcv.vn/viec-lam/guarded")
        assert result.status == "BLOCKED"
        assert result.error and result.error.startswith("WAF_CHALLENGE")


# ==============================================================================
# 5. Adapter parse_raw — ưu tiên detail-enriched payload
# ==============================================================================

class TestAdapterParseRawWithDetail:
    @pytest.mark.asyncio
    async def test_itviec_prefers_payload_description(self):
        collector = ITViecJobCollector()
        raw = RawJobData(
            source="itviec",
            source_url="https://itviec.com/it-jobs/test",
            raw_payload={
                "title": "Backend Developer (Python)",
                "company": "ACME",
                "location": "Ho Chi Minh City",
                "description": "FULL DETAIL JD:\nWe build distributed data pipelines. " * 3,
                "skills": ["Python"],
                "posted_iso": "2026-10-30T09:00:00+07:00",
            },
            raw_html="<div>thin card text</div>",
            content_hash="a" * 64,
        )
        extracted = await collector.parse_raw(raw)
        assert "FULL DETAIL JD" in extracted.description
        assert "thin card text" not in extracted.description
        assert extracted.posted_at is not None and extracted.posted_at.year == 2026

    @pytest.mark.asyncio
    async def test_topcv_falls_back_to_card_when_no_detail(self):
        collector = TopCVJobCollector()
        raw = RawJobData(
            source="topcv",
            source_url="https://www.topcv.vn/viec-lam/x/1.html",
            raw_payload={"title": "Fullstack Developer", "company": "VNG Corp",
                         "location": "Ha Noi", "skills": ["NodeJS"]},
            raw_html="<div><h3>Fullstack job card listing text</h3></div>",
            content_hash="b" * 64,
        )
        extracted = await collector.parse_raw(raw)
        assert "Fullstack job card listing text" in extracted.description


# ==============================================================================
# 6. Pipeline Integration (SQLite in-memory + mocked fetch_detail)
# ==============================================================================

class _StubITViecCollector(BaseJobCollector):
    """Collector giả lập listing ITViec mỏng (chỉ card) để test enrichment."""

    @property
    def source_name(self) -> str:
        return "itviec"

    async def fetch_jobs(self, limit: int = 20):
        payload = {
            "title": "Data Engineer",
            "company": "ACME Vietnam",
            "location": "Ho Chi Minh City",
            "url": "https://itviec.com/it-jobs/data-engineer-stub",
            "skills": ["Python", "SQL"],
        }
        return [
            RawJobData(
                source=self.source_name,
                source_url=payload["url"],
                source_job_id="data-engineer-stub",
                raw_payload=payload,
                raw_html="<div>short card</div>",
                content_hash=BaseJobCollector.compute_content_hash(
                    f"{payload['title']}|{payload['company']}|{payload['location']}|{payload['url']}"
                ),
            )
        ]

    async def parse_raw(self, raw: RawJobData) -> JobExtractedData:
        payload = raw.raw_payload or {}
        desc = str(payload.get("description") or "").strip()
        if not desc:
            desc = "short card"
        return JobExtractedData(
            title=payload["title"],
            company_name=payload["company"],
            location=payload.get("location") or "Ho Chi Minh City",
            description=desc,
            skills_required=payload.get("skills", []),
        )


class _StubMultiJobCollector(_StubITViecCollector):
    """Stub sinh nhiều listing mỏng để kiểm tra trần (budget) của detail fetch."""

    _TITLES = ("Data Engineer", "Backend Engineer", "DevOps Engineer")

    async def fetch_jobs(self, limit: int = 20):
        jobs = []
        for i in range(limit):
            payload = {
                "title": f"{self._TITLES[i % len(self._TITLES)]} (Level {i})",
                "company": "ACME Vietnam",
                "location": "Ho Chi Minh City",
                "url": f"https://itviec.com/it-jobs/job-stub-{i}",
                "skills": ["Python", "SQL"],
            }
            jobs.append(
                RawJobData(
                    source=self.source_name,
                    source_url=payload["url"],
                    source_job_id=f"stub-{i}",
                    raw_payload=payload,
                    raw_html="<div>short card</div>",
                    content_hash=BaseJobCollector.compute_content_hash(
                        f"{payload['title']}|{payload['company']}|{payload['location']}|{payload['url']}"
                    ),
                )
            )
        return jobs


class TestPipelineDetailEnrichment:
    @pytest.mark.asyncio
    async def test_success_enrichment_persists_full_jd(self, async_db_session, monkeypatch):
        full_jd = (
            "MÔ TẢ CÔNG VIỆC:\n"
            + "Thiết kế pipeline dữ liệu trên AWS với Spark và Airflow. " * 30
            + "\n\nYÊU CẦU:\n- 3+ năm kinh nghiệm Python, Kafka."
        )
        detail = JobDetailResult(
            source="itviec",
            url="https://itviec.com/it-jobs/data-engineer-stub",
            status="OK",
            description=full_jd,
            posted_at=datetime(2026, 10, 30, 9, 0, tzinfo=timezone.utc),
            employment_type="FULL_TIME",
            skills=["Spark", "Airflow"],
            method="jsonld",
            attempts=1,
        )

        async def fake_fetch_detail(source, url, max_attempts=2, timeout=10.0):
            return detail

        monkeypatch.setattr(detail_fetcher, "fetch_detail", fake_fetch_detail)

        stats = await ingestion_pipeline.run(
            _StubITViecCollector(), async_db_session, limit=1, fetch_details=True
        )
        logger.info(f"Stats: created={stats.created}, enriched={stats.details_enriched}, failed={stats.details_failed}")
        assert stats.created == 1
        assert stats.details_enriched == 1
        assert stats.details_failed == 0

        job = (await async_db_session.execute(select(Job))).scalars().first()
        assert job is not None and "Spark và Airflow" in job.description
        assert len(job.description) > 500

        raw_job = (await async_db_session.execute(select(RawJob))).scalars().first()
        payload = raw_job.raw_payload or {}
        assert "detail_meta" in payload and payload["detail_meta"]["method"] == "jsonld"
        assert payload["posted_iso"].startswith("2026-10-30")
        # Skills union: listing skills + detail skills đều tồn tại
        assert "Spark" in payload["skills"] and "Python" in payload["skills"]

    @pytest.mark.asyncio
    async def test_blocked_detail_degrades_gracefully_to_listing(self, async_db_session, monkeypatch):
        blocked = JobDetailResult(
            source="itviec",
            url="https://itviec.com/it-jobs/data-engineer-stub",
            status="BLOCKED",
            error="WAF_CHALLENGE:CHALLENGE_TITLE",
            attempts=1,
        )

        async def fake_fetch_detail(source, url, max_attempts=2, timeout=10.0):
            return blocked

        monkeypatch.setattr(detail_fetcher, "fetch_detail", fake_fetch_detail)

        stats = await ingestion_pipeline.run(
            _StubITViecCollector(), async_db_session, limit=1, fetch_details=True
        )
        logger.info(f"Stats: created={stats.created}, enriched={stats.details_enriched}, failed={stats.details_failed}")
        # Vẫn tạo job thành công với dữ liệu listing (graceful degradation)
        assert stats.created == 1
        assert stats.details_enriched == 0
        assert stats.details_failed == 1

        raw_job = (await async_db_session.execute(select(RawJob))).scalars().first()
        assert raw_job.fetch_status == "PARSED"
        assert (raw_job.raw_payload or {}).get("detail_meta", {}).get("status") == "BLOCKED"

    @pytest.mark.asyncio
    async def test_unsupported_source_skips_enrichment(self, async_db_session, monkeypatch):
        from app.services.collectors.mock_adapter import MockJobCollector

        async def fail_if_called(source, url, max_attempts=2, timeout=10.0):  # pragma: no cover
            raise AssertionError("fetch_detail không được gọi cho nguồn unsupported")

        monkeypatch.setattr(detail_fetcher, "fetch_detail", fail_if_called)

        stats = await ingestion_pipeline.run(
            MockJobCollector(), async_db_session, limit=2, fetch_details=True
        )
        assert stats.created == 2
        assert stats.details_enriched == 0
        assert stats.details_failed == 0

    @pytest.mark.asyncio
    async def test_budget_limit_stops_extra_fetches(self, async_db_session, monkeypatch):
        from app.core.config import settings

        calls = {"n": 0}

        async def fake_fetch_detail(source, url, max_attempts=2, timeout=10.0):
            calls["n"] += 1
            return JobDetailResult(
                source=source, url=url, status="OK",
                description="Enriched full JD body. " * 300, method="generic",
            )

        monkeypatch.setattr(detail_fetcher, "fetch_detail", fake_fetch_detail)
        original = settings.DETAIL_FETCH_MAX_PER_RUN
        try:
            settings.DETAIL_FETCH_MAX_PER_RUN = 1
            stats = await ingestion_pipeline.run(
                _StubMultiJobCollector(), async_db_session, limit=3, fetch_details=True
            )
        finally:
            settings.DETAIL_FETCH_MAX_PER_RUN = original

        # Budget = 1: chỉ 1 lần fetch_detail được gọi; còn lại bị skip
        assert calls["n"] == 1
        assert stats.details_enriched == 1
        assert stats.details_skipped == 2
        assert stats.created == 3


# ==============================================================================
# Helper: URLFetcher mocking helpers
# ==============================================================================

def _fake_doc(html: str, clean_text: str = "", method: str = "httpx", status_code: int = 200, json_ld: dict | None = None):
    from bs4 import BeautifulSoup

    from app.services.extraction.url_fetcher import FetchedDocument

    soup = BeautifulSoup(html, "html.parser")
    # Parse JSON-LD TRƯỚC khi decompose script tags
    if json_ld is None and 'application/ld+json' in html:
        import json as _json
        scripts = soup.find_all("script", type="application/ld+json")
        for s in scripts:
            try:
                json_ld = _json.loads(s.string or "")
                break
            except Exception:
                continue
    if not clean_text:
        for tag in soup(["script", "style"]):
            tag.decompose()
        clean_text = soup.get_text("\n", strip=True)
    # Nếu HTML chứa JSON-LD, parse luôn để test jsonld path
    return FetchedDocument(
        url="https://stub", final_url="https://stub", status_code=status_code,
        content_type="text/html", html=html, title=soup.title.get_text(strip=True) if soup.title else None,
        meta_description=None, og_title=None, og_description=None,
        json_ld=json_ld, clean_text=clean_text, fetch_method=method,
    )


def _failed_doc(error: str, status_code: int = 0):
    from app.services.extraction.url_fetcher import FetchedDocument

    return FetchedDocument(
        url="https://stub", final_url="https://stub", status_code=status_code,
        content_type="", html=None, title=None, meta_description=None,
        og_title=None, og_description=None, json_ld=None, clean_text="",
        fetch_method="failed", error=error,
    )


def _patch_url_fetcher(monkeypatch, fetch_callable):
    import importlib
    uf_module = importlib.import_module("app.services.extraction.url_fetcher")
    monkeypatch.setattr(uf_module.url_fetcher, "fetch", fetch_callable)


def _async_return(value):
    async def _inner(*args, **kwargs):
        return value
    return _inner
