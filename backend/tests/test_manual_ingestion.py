import logging
import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.models.job import Job, RawJob
from app.schemas.job import ManualJobIngestRequest
from app.services.extraction.heuristic_extractor import heuristic_extractor
from app.services.extraction.url_fetcher import url_fetcher

logger = logging.getLogger("test.manual_ingestion")


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
async def test_heuristic_extraction_vietnamese_post():
    """Kiểm tra trích xuất bài đăng Facebook tiếng Việt với emojis, mức lương triệu VND, HR email, SĐT Zalo."""
    raw_post = """
    🔥 [Tuyển dụng] Senior Backend Developer (Python / FastAPI) 🔥
    Công ty: VNG Corporation
    Địa điểm: Tòa nhà VNG Campus, Quận 7, TP.HCM (Hỗ trợ Hybrid 2 ngày WFH)
    Mức lương: 25 - 45 triệu VND (deal theo năng lực)

    Mô tả công việc & Yêu cầu:
    - 3+ năm kinh nghiệm phát triển hệ thống với Python, FastAPI, Django
    - Sử dụng thành thạo PostgreSQL, Redis, Docker, Kafka
    - Hiểu biết về CI/CD, Microservices và AWS Cloud
    - Điểm cộng: Có kinh nghiệm với Kubernetes và Golang

    Quyền lợi:
    - Thưởng lương tháng 13 + performance bonus
    - Bảo hiểm sức khỏe cao cấp Bảo Việt

    📩 CV gửi về: hr-tech@vng.com.vn (hoặc liên hệ Zalo: 0901234567 gặp Ms. Lan)
    """

    res = heuristic_extractor.extract(raw_post)

    assert res.extraction_status == "PARSED"
    assert res.overall_confidence >= 0.70
    assert "Python" in res.data.title or "Backend" in res.data.title
    assert "VNG" in res.data.company_name
    assert res.data.min_salary == 25_000_000
    assert res.data.max_salary == 45_000_000
    assert res.data.salary_currency == "VND"
    assert res.data.contact_email == "hr-tech@vng.com.vn"
    assert res.data.level.value == "SENIOR"
    assert res.data.work_mode.value in ("HYBRID", "ONSITE")
    assert "Python" in res.data.skills_required or "FastAPI" in res.data.skills_required
    assert "PostgreSQL" in res.data.skills_required

    # Check field confidences
    field_names = [f.field for f in res.fields if f.detected]
    assert "title" in field_names
    assert "company" in field_names
    assert "salary" in field_names
    assert "skills" in field_names
    assert "contact" in field_names


@pytest.mark.asyncio
async def test_heuristic_extraction_english_post():
    """Kiểm tra trích xuất JD tiếng Anh dạng LinkedIn/Remote với mức lương USD."""
    raw_post = """
    Role: Mid-level Golang Engineer
    Company: CyberTech Global Ltd
    Location: Remote - Worldwide (Work from home)
    Salary: $1,800 - $3,200 USD

    Job Description:
    We are looking for a skilled Golang Developer to join our distributed infrastructure team.
    Requirements:
    - 2+ years of experience with Go (Golang)
    - Strong database skills with PostgreSQL, MySQL, Redis
    - Hands-on experience with Docker, Kubernetes, AWS
    - Good English communication skills

    Please send your resume to careers@cybertech.io with subject [Golang Application].
    """

    res = heuristic_extractor.extract(raw_post)

    assert res.extraction_status == "PARSED"
    assert "Golang" in res.data.title or "Engineer" in res.data.title
    assert "CyberTech" in res.data.company_name
    assert res.data.min_salary == 1800.0
    assert res.data.max_salary == 3200.0
    assert res.data.salary_currency == "USD"
    assert res.data.work_mode.value == "REMOTE"
    assert res.data.contact_email == "careers@cybertech.io"
    assert "Go" in res.data.skills_required or "Golang" in res.data.skills_required


@pytest.mark.asyncio
async def test_heuristic_extraction_partial_and_warnings():
    """Kiểm tra bài đăng thiếu nhiều thông tin -> Trạng thái PARTIAL và có warnings."""
    sparse_post = """
    Cần tuyển gấp Lập trình viên ReactJS
    Yêu cầu biết HTML, CSS, JavaScript, React. Lương thỏa thuận khi phỏng vấn.
    """

    res = heuristic_extractor.extract(sparse_post)

    assert res.extraction_status in ("PARTIAL", "PARSED")
    assert len(res.warnings) > 0
    assert any("Location" in w or "Company" in w for w in res.warnings)
    assert res.data.is_salary_negotiable is True


@pytest.mark.asyncio
async def test_url_fetcher_html_parsing():
    """Kiểm tra URLFetcher bóc tách metadata, JSON-LD và clean text từ HTML."""
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
      <title>Senior DevOps Engineer - Cloud Corp</title>
      <meta property="og:title" content="Senior DevOps Engineer at Cloud Corp">
      <meta property="og:description" content="Join our DevOps team in Hanoi. Great salary and benefits.">
      <script type="application/ld+json">
      {
        "@type": "JobPosting",
        "title": "Senior DevOps Engineer",
        "hiringOrganization": { "@type": "Organization", "name": "Cloud Corp" }
      }
      </script>
    </head>
    <body>
      <nav><a href="/">Home</a><a href="/jobs">Jobs</a></nav>
      <main class="job-detail">
        <h1>Senior DevOps Engineer</h1>
        <div class="company">Cloud Corp</div>
        <div class="description">
          <p>We are seeking a Senior DevOps Engineer in Hanoi.</p>
          <p>Requirements: Docker, Kubernetes, Terraform, AWS, CI/CD pipelines.</p>
          <p>Salary: $2,000 - $3,500. Contact: jobs@cloudcorp.com</p>
        </div>
      </main>
      <footer>Copyright 2026</footer>
    </body>
    </html>
    """

    doc = url_fetcher.parse_html(
        url="https://cloudcorp.com/careers/123",
        final_url="https://cloudcorp.com/careers/123",
        status_code=200,
        content_type="text/html",
        html_content=sample_html,
    )

    assert doc.fetch_method == "httpx"
    assert doc.title == "Senior DevOps Engineer - Cloud Corp"
    assert doc.og_title == "Senior DevOps Engineer at Cloud Corp"
    assert doc.json_ld is not None
    assert doc.json_ld.get("title") == "Senior DevOps Engineer"
    assert "Copyright" not in doc.clean_text  # Footer stripped
    assert "Docker" in doc.clean_text


@pytest.mark.asyncio
async def test_url_fetcher_js_required_fallback():
    """Kiểm tra URLFetcher phát hiện trang SPA/React rỗng cần JS rendering."""
    spa_html = """
    <!DOCTYPE html>
    <html>
    <head><title>Careers App</title></head>
    <body>
      <div id="root"></div>
      <script src="/static/bundle.js"></script>
    </body>
    </html>
    """

    doc = url_fetcher.parse_html(
        url="https://spa-company.com/job/456",
        final_url="https://spa-company.com/job/456",
        status_code=200,
        content_type="text/html",
        html_content=spa_html,
    )

    assert doc.fetch_method == "failed"
    assert doc.error == "JS_REQUIRED"


@pytest.mark.asyncio
async def test_manual_ingest_api_created_and_auto_match(test_client):
    """
    Kiểm thử toàn diện API POST /api/v1/jobs/ingest-manual:
    1. Nạp Candidate Profile vào DB
    2. Gọi POST /api/v1/jobs/ingest-manual
    3. Xác nhận response status='created', Job lưu DB, Match score được tính tức thì.
    """
    client, session_factory = test_client
    headers = {"X-Internal-Secret": settings.INTERNAL_API_SECRET}

    # 1. Sync candidate profile
    sync_res = await client.post("/api/v1/profile/sync", headers=headers)
    assert sync_res.status_code == 200

    # 2. Ingest manual raw text job
    payload = {
        "mode": "text",
        "raw_text": """
        [Tuyển dụng] Senior Golang & Python Developer
        Công ty: TechNova Solutions
        Địa điểm: Ho Chi Minh City / Hybrid
        Mức lương: $2,000 - $3,000
        Yêu cầu:
        - Thành thạo Golang, Python, PostgreSQL, Redis, Docker, Microservices
        - 3+ năm kinh nghiệm phát triển backend
        Liên hệ: hr@technova.io
        """,
        "auto_match": True,
    }

    res = await client.post("/api/v1/jobs/ingest-manual", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["status"] in ("created", "partial")
    assert data["job"] is not None
    assert "Golang" in data["job"]["title"] or "Python" in data["job"]["title"]
    assert "TechNova" in data["job"]["company_name"]
    assert data["job"]["source"] == "manual"

    # Match score should be computed
    assert data["match"] is not None
    assert "score" in data["match"]
    assert data["match"]["score"] > 0

    # Extraction metadata should be populated
    assert data["extraction_metadata"] is not None
    assert data["extraction_metadata"]["method"] in ("heuristic", "llm", "heuristic+llm")
    assert len(data["extraction_metadata"]["fields"]) > 0


@pytest.mark.asyncio
async def test_manual_ingest_api_duplicate_handling(test_client):
    """Kiểm tra xử lý trùng lặp khi nạp lại cùng một JD thủ công."""
    client, session_factory = test_client
    headers = {"X-Internal-Secret": settings.INTERNAL_API_SECRET}

    await client.post("/api/v1/profile/sync", headers=headers)

    payload = {
        "mode": "text",
        "raw_text": """
        Tuyển gấp: Fullstack Developer (Node.js & React)
        Công ty: Apex Software JSC
        Địa điểm: Hanoi
        Lương: 20 - 35 triệu
        Yêu cầu: Node.js, React, TypeScript, MongoDB, Docker
        Email: tuyển.dung@apex.vn
        """,
        "auto_match": True,
    }

    # Lần 1: Tạo mới
    res1 = await client.post("/api/v1/jobs/ingest-manual", json=payload, headers=headers)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] in ("created", "partial")
    job_id_1 = data1["job"]["id"]

    # Lần 2: Nạp lại cùng JD -> Trả về duplicate
    res2 = await client.post("/api/v1/jobs/ingest-manual", json=payload, headers=headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "duplicate"
    assert data2["job"]["id"] == job_id_1
    assert "đã tồn tại" in data2["message"].lower() or "exists" in data2["message"].lower()


@pytest.mark.asyncio
async def test_manual_ingest_api_validation(test_client):
    """Kiểm tra validation lỗi đầu vào."""
    client, session_factory = test_client
    headers = {"X-Internal-Secret": settings.INTERNAL_API_SECRET}

    # Text quá ngắn (<30 chars)
    res_short = await client.post(
        "/api/v1/jobs/ingest-manual",
        json={"mode": "text", "raw_text": "Tuyển dev"},
        headers=headers,
    )
    assert res_short.status_code == 200
    assert res_short.json()["status"] == "failed"

    # URL không hợp lệ
    res_url = await client.post(
        "/api/v1/jobs/ingest-manual",
        json={"mode": "url", "url": "invalid-url"},
        headers=headers,
    )
    assert res_url.status_code == 200
    assert res_url.json()["status"] == "failed"


@pytest.mark.asyncio
async def test_raw_job_provenance_and_database_persistence(test_client):
    """Kiểm tra RawJob lưu đúng provenance metadata và Job liên kết đầy đủ skills."""
    client, session_factory = test_client
    headers = {"X-Internal-Secret": settings.INTERNAL_API_SECRET}

    payload = {
        "mode": "text",
        "raw_text": """
        Vị trí: AI Engineer (LLM & Computer Vision)
        Công ty: CyberAI Labs Vietnam
        Địa điểm: Da Nang / Remote
        Mức lương: $1,500 - $2,500
        Yêu cầu: Python, PyTorch, LangChain, OpenAI API, Docker, FastAPI
        Liên hệ: hr@cyberai.vn
        """,
        "auto_match": False,
    }

    res = await client.post("/api/v1/jobs/ingest-manual", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    job_id = uuid.UUID(data["job"]["id"])

    # Query DB directly to verify persistence
    async with session_factory() as session:
        stmt = select(Job).where(Job.id == job_id)
        job_result = await session.execute(stmt)
        job = job_result.scalar_one_or_none()
        assert job is not None

        # Verify RawJob provenance
        stmt_raw = select(RawJob).where(RawJob.id == job.raw_job_id)
        raw_result = await session.execute(stmt_raw)
        raw_job = raw_result.scalar_one_or_none()
        assert raw_job is not None
        assert raw_job.source == "manual"
        assert raw_job.raw_payload["ingestion_method"] == "text"
        assert raw_job.raw_payload["extraction_method"] == "heuristic"
        assert "original_input" in raw_job.raw_payload
        assert len(raw_job.raw_payload["field_confidences"]) > 0
