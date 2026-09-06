import logging
import pytest
from app.services.collectors.base import RawJobData
from app.services.collectors.careerlink_adapter import CareerLinkJobCollector
from app.services.collectors.growupwork_adapter import GrowUpWorkJobCollector
from app.services.collectors.itnavi_adapter import ITNaviJobCollector
from app.services.collectors.itviec_adapter import ITViecJobCollector
from app.services.collectors.mock_adapter import MockJobCollector
from app.services.collectors.remotive_adapter import RemotiveJobCollector
from app.services.collectors.topcv_adapter import TopCVJobCollector
from app.services.collectors.topdev_adapter import TopDevJobCollector
from app.services.collectors.upwork_adapter import UpworkJobCollector
from app.services.collectors.vietnamworks_adapter import VietnamWorksJobCollector

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


@pytest.mark.asyncio
async def test_itviec_parser():
    """Kiểm tra ITViecJobCollector bóc tách dữ liệu từ raw payload & html."""
    logger.info("=== [TEST] ITViecJobCollector Parsing ===")
    collector = ITViecJobCollector()
    assert collector.source_name == "itviec"

    raw = RawJobData(
        source="itviec",
        source_url="https://itviec.com/it-jobs/expert-ios-engineer-techcombank",
        source_job_id="expert-ios-engineer-techcombank",
        raw_payload={
            "title": "Expert, iOS Software Engineer",
            "company": "Techcombank",
            "location": "Ha Noi",
            "skills": ["iOS", "Swift", "Objective-C"],
            "salary_text": "Negotiable",
        },
        raw_html="<div><p>We need iOS Swift master</p></div>",
        content_hash="f"*64,
    )

    extracted = await collector.parse_raw(raw)
    assert extracted.title == "Expert, iOS Software Engineer"
    assert extracted.company_name == "Techcombank"
    assert "Swift" in extracted.skills_required
    assert "Ha Noi" in extracted.location


@pytest.mark.asyncio
async def test_topdev_parser():
    """Kiểm tra TopDevJobCollector bóc tách dữ liệu và xác định work_mode."""
    logger.info("=== [TEST] TopDevJobCollector Parsing ===")
    collector = TopDevJobCollector()
    assert collector.source_name == "topdev"

    raw = RawJobData(
        source="topdev",
        source_url="https://topdev.vn/detail-jobs/senior-backend-python-remote-12345",
        source_job_id="12345",
        raw_payload={
            "title": "Senior Backend Developer (Remote)",
            "company": "KMS Technology",
            "location": "Ho Chi Minh City",
            "skills": ["Python", "FastAPI", "Docker"],
            "salary_text": "$2000 - $3000",
        },
        raw_html="<div>Senior Backend Developer (Remote) at KMS</div>",
        content_hash="1"*64,
    )

    extracted = await collector.parse_raw(raw)
    assert extracted.title == "Senior Backend Developer (Remote)"
    assert extracted.company_name == "KMS Technology"
    assert extracted.work_mode.value == "REMOTE"
    assert "FastAPI" in extracted.skills_required


@pytest.mark.asyncio
async def test_itnavi_parser():
    """Kiểm tra ITNaviJobCollector bóc tách dữ liệu."""
    logger.info("=== [TEST] ITNaviJobCollector Parsing ===")
    collector = ITNaviJobCollector()
    assert collector.source_name == "itnavi"

    raw = RawJobData(
        source="itnavi",
        source_url="https://itnavi.com.vn/job/reactjs-developer-99",
        source_job_id="99",
        raw_payload={
            "title": "Frontend ReactJS Developer",
            "company": "FPT Software",
            "location": "Da Nang",
            "skills": ["ReactJS", "TypeScript"],
            "salary_text": "15 - 25 triệu",
        },
        raw_html="<div>Frontend ReactJS Developer tại FPT Software</div>",
        content_hash="2"*64,
    )

    extracted = await collector.parse_raw(raw)
    assert extracted.title == "Frontend ReactJS Developer"
    assert extracted.company_name == "FPT Software"
    assert "ReactJS" in extracted.skills_required


@pytest.mark.asyncio
async def test_growupwork_parser():
    """Kiểm tra GrowUpWorkJobCollector bóc tách dữ liệu việc làm tiếng Nhật."""
    logger.info("=== [TEST] GrowUpWorkJobCollector Parsing ===")
    collector = GrowUpWorkJobCollector()
    assert collector.source_name == "growupwork"

    raw = RawJobData(
        source="growupwork",
        source_url="https://growupwork.com/job/brse-n2-tokyo-77",
        source_job_id="77",
        raw_payload={
            "title": "Bridge Software Engineer (BrSE N2)",
            "company": "NTT Data",
            "location": "Tokyo, Japan",
            "skills": ["Java", "Japanese N2", "AWS"],
            "salary_text": "400 - 600 man/year",
        },
        raw_html="<div>BrSE N2 tại NTT Data Tokyo</div>",
        content_hash="3"*64,
    )

    extracted = await collector.parse_raw(raw)
    assert extracted.title == "Bridge Software Engineer (BrSE N2)"
    assert extracted.company_name == "NTT Data"
    assert "Japanese N2" in extracted.skills_required


@pytest.mark.asyncio
async def test_vietnamworks_parser():
    """Kiểm tra VietnamWorksJobCollector bóc tách dữ liệu."""
    logger.info("=== [TEST] VietnamWorksJobCollector Parsing ===")
    collector = VietnamWorksJobCollector()
    assert collector.source_name == "vietnamworks"

    raw = RawJobData(
        source="vietnamworks",
        source_url="https://www.vietnamworks.com/devops-cloud-engineer-jv123",
        source_job_id="123",
        raw_payload={
            "title": "DevOps Cloud Engineer (Kubernetes)",
            "company": "Shopee Vietnam",
            "location": "Ho Chi Minh City",
            "skills": ["Kubernetes", "Terraform", "CI/CD"],
            "salary_text": "Negotiable",
        },
        raw_html="<div>DevOps Cloud Engineer tại Shopee</div>",
        content_hash="4"*64,
    )

    extracted = await collector.parse_raw(raw)
    assert extracted.title == "DevOps Cloud Engineer (Kubernetes)"
    assert extracted.company_name == "Shopee Vietnam"
    assert "Kubernetes" in extracted.skills_required


@pytest.mark.asyncio
async def test_upwork_parser():
    """Kiểm tra UpworkJobCollector bóc tách dữ liệu remote RSS."""
    logger.info("=== [TEST] UpworkJobCollector Parsing ===")
    collector = UpworkJobCollector()
    assert collector.source_name == "upwork"

    raw = RawJobData(
        source="upwork",
        source_url="https://www.upwork.com/jobs/~01abcdef123456",
        source_job_id="01abcdef123456",
        raw_payload={
            "title": "Python FastAPI Microservices Developer",
            "company": "Upwork Client (United States)",
            "location": "Worldwide (Remote)",
            "country": "United States",
            "skills": ["Python", "FastAPI", "PostgreSQL"],
            "clean_description": "Need an expert in Python and FastAPI to build RESTful services.",
            "pub_date_str": "Wed, 01 Sep 2026 12:00:00 GMT",
        },
        raw_html="Need an expert in Python and FastAPI to build RESTful services.",
        content_hash="5"*64,
    )

    extracted = await collector.parse_raw(raw)
    assert extracted.title == "Python FastAPI Microservices Developer"
    assert extracted.work_mode.value == "REMOTE"
    assert extracted.company_name == "Upwork Client (United States)"
    assert "FastAPI" in extracted.skills_required

