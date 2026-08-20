import logging
import pytest
from app.services.collectors.base import RawJobData
from app.services.collectors.careerlink_adapter import CareerLinkJobCollector
from app.services.collectors.itviec_adapter import ITViecJobCollector
from app.services.collectors.mock_adapter import MockJobCollector
from app.services.collectors.remotive_adapter import RemotiveJobCollector
from app.services.collectors.topcv_adapter import TopCVJobCollector

logger = logging.getLogger("test.adapters")


@pytest.mark.asyncio
async def test_mock_collector_fetch_and_parse():
    """Kiểm tra MockJobCollector trả về dữ liệu đúng định dạng và parse được."""
    logger.info("=== [TEST] MockJobCollector Fetch and Parse ===")
    collector = MockJobCollector()
    assert collector.source_name == "mock"

    jobs = await collector.fetch_jobs(limit=2)
    logger.info(f"  Fetched {len(jobs)} mock jobs")
    assert len(jobs) == 2
    assert isinstance(jobs[0], RawJobData)
    assert jobs[0].source == "mock"
    assert len(jobs[0].content_hash) == 64
    logger.info(f"  Mock Job 1 Content Hash: {jobs[0].content_hash}")

    # Test parser
    extracted = await collector.parse_raw(jobs[0])
    logger.info(f"  Parsed Job Title: '{extracted.title}'")
    logger.info(f"  Parsed Company: '{extracted.company_name}'")
    logger.info(f"  Parsed Skills Required: {extracted.skills_required}")
    assert extracted.title != ""
    assert extracted.company_name != ""
    assert len(extracted.skills_required) > 0


@pytest.mark.asyncio
async def test_remotive_parser_html_cleanup():
    """Kiểm tra RemotiveJobCollector làm sạch mã nguồn HTML description."""
    logger.info("=== [TEST] RemotiveJobCollector HTML Description Cleanup ===")
    collector = RemotiveJobCollector()
    raw_html_input = "<p>We are seeking a <strong>Python Expert</strong> with FastAPI.</p>"
    
    raw = RawJobData(
        source="remotive",
        source_url="https://remotive.com/job/999",
        source_job_id="999",
        raw_payload={
            "id": 999,
            "title": "Staff Python Engineer",
            "company_name": "Acme Remote Inc",
            "candidate_required_location": "Worldwide",
            "description": raw_html_input,
            "tags": ["Python", "FastAPI"],
            "publication_date": "2026-08-20T10:00:00Z",
        },
        content_hash="c"*64,
    )
    logger.info(f"  Raw HTML Input: {raw_html_input}")

    extracted = await collector.parse_raw(raw)
    logger.info(f"  Extracted Clean Description: '{extracted.description}'")
    logger.info(f"  Extracted Tags/Skills: {extracted.skills_required}")
    
    assert extracted.title == "Staff Python Engineer"
    assert extracted.company_name == "Acme Remote Inc"
    assert "<p>" not in extracted.description
    assert "Python Expert with FastAPI." in extracted.description
    assert "FastAPI" in extracted.skills_required


@pytest.mark.asyncio
async def test_careerlink_parser():
    """Kiểm tra CareerLinkJobCollector bóc tách dữ liệu từ raw card."""
    logger.info("=== [TEST] CareerLinkJobCollector Parsing ===")
    collector = CareerLinkJobCollector()
    assert collector.source_name == "careerlink"

    raw_card_html = """
    <div class="list-group-item job-item">
        <a class="job-link" href="/tim-viec-lam/senior-devops-engineer/12345">Senior DevOps Engineer</a>
        <a class="job-company" href="/nha-tuyen-dung/tech-group/99">Tech Group Vietnam</a>
        <div class="job-location">Ho Chi Minh City</div>
        <span class="job-salary">$2,000 - $3,500</span>
        <a class="job-position">DevOps</a>
    </div>
    """

    raw = RawJobData(
        source="careerlink",
        source_url="https://www.careerlink.vn/tim-viec-lam/senior-devops-engineer/12345",
        source_job_id="12345",
        raw_payload={
            "title": "Senior DevOps Engineer",
            "company": "Tech Group Vietnam",
            "location": "Ho Chi Minh City",
            "url": "https://www.careerlink.vn/tim-viec-lam/senior-devops-engineer/12345",
            "salary_text": "$2,000 - $3,500",
            "skills": ["DevOps"],
        },
        raw_html=raw_card_html,
        content_hash="d"*64,
    )

    extracted = await collector.parse_raw(raw)
    logger.info(f"  Extracted Title: '{extracted.title}', Company: '{extracted.company_name}', Skills: {extracted.skills_required}")
    assert extracted.title == "Senior DevOps Engineer"
    assert extracted.company_name == "Tech Group Vietnam"
    assert extracted.skills_required == ["DevOps"]


@pytest.mark.asyncio
async def test_topcv_parser():
    """Kiểm tra TopCVJobCollector bóc tách dữ liệu từ raw card."""
    logger.info("=== [TEST] TopCVJobCollector Parsing ===")
    collector = TopCVJobCollector()
    assert collector.source_name == "topcv"

    raw_card_html = """
    <div class="job-item-search-result">
        <h3 class="title"><a href="https://www.topcv.vn/viec-lam/fullstack-developer/888.html">Fullstack Developer (NodeJS / React)</a></h3>
        <a class="company" href="https://www.topcv.vn/cong-ty/vng">VNG Corp</a>
        <div class="address">Ha Noi</div>
        <div class="salary">25 - 35 triệu</div>
        <span class="tag">NodeJS</span>
        <span class="tag">React</span>
    </div>
    """

    raw = RawJobData(
        source="topcv",
        source_url="https://www.topcv.vn/viec-lam/fullstack-developer/888.html",
        source_job_id="888",
        raw_payload={
            "title": "Fullstack Developer (NodeJS / React)",
            "company": "VNG Corp",
            "location": "Ha Noi",
            "url": "https://www.topcv.vn/viec-lam/fullstack-developer/888.html",
            "salary_text": "25 - 35 triệu",
            "skills": ["NodeJS", "React"],
        },
        raw_html=raw_card_html,
        content_hash="e"*64,
    )

    extracted = await collector.parse_raw(raw)
    logger.info(f"  Extracted Title: '{extracted.title}', Company: '{extracted.company_name}', Skills: {extracted.skills_required}")
    assert extracted.title == "Fullstack Developer (NodeJS / React)"
    assert extracted.company_name == "VNG Corp"
    assert "NodeJS" in extracted.skills_required
    assert "React" in extracted.skills_required
