import io
import logging
from pathlib import Path
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from pypdf import PdfWriter

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.services.parser import CandidateProfileParser

logger = logging.getLogger("test.pdf_and_upload")


def create_minimal_pdf(text: str) -> bytes:
    """Tạo một file PDF cơ bản trong bộ nhớ để kiểm thử parse_pdf."""
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    # Add metadata
    writer.add_metadata({
        "/Title": "Resume - Test Candidate",
        "/Author": "Test Candidate",
    })
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest_asyncio.fixture
async def test_client():
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
        yield client

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_candidate_profile_parser_raw_files():
    """Kiểm tra parser hoạt động chính xác với các định dạng khác nhau."""
    # 1. LaTeX format
    latex_sample = r"""
    \documentclass{article}
    \begin{document}
    {\huge \textbf{Jane Doe}} \\
    {\Large \textbf{Backend Engineer}} \\
    \href{mailto:janedoe@example.com}{janedoe@example.com} \quad
    \href{https://github.com/janedoe}{github.com/janedoe} \quad
    \href{https://www.linkedin.com/in/janedoe}{linkedin.com/in/janedoe} \quad
    \quad Ho Chi Minh City \quad
    \section*{Objective}
    Experienced Python and FastAPI backend developer.
    \section*{Skills}
    \begin{itemize}
        \item \textbf{Programming Languages:} Python, TypeScript, SQL
        \item \textbf{Frameworks:} FastAPI, Django, React
        \item \textbf{Tools:} Docker, PostgreSQL, Redis
    \end{itemize}
    \end{document}
    """
    parsed_tex = CandidateProfileParser.parse_raw_file("master-resume.tex", latex_sample.encode("utf-8"))
    assert parsed_tex["candidate"]["name"] == "Jane Doe"
    assert parsed_tex["candidate"]["email"] == "janedoe@example.com"
    assert "Python" in parsed_tex["skills"]["programming"]
    assert "FastAPI" in parsed_tex["skills"]["frameworks"]

    # 2. YAML format
    yaml_sample = """
    candidate:
      name: "Alice Smith"
      headline: "DevOps Engineer"
      email: "alice@example.com"
      location: "Hanoi, Vietnam"
    skills:
      programming:
        - "Python"
        - "Go"
      tools_databases:
        - "Docker"
        - "Kubernetes"
    """
    parsed_yaml = CandidateProfileParser.parse_raw_file("candidate-profile.yaml", yaml_sample.encode("utf-8"))
    assert parsed_yaml["candidate"]["name"] == "Alice Smith"
    assert parsed_yaml["candidate"]["email"] == "alice@example.com"
    assert "Go" in parsed_yaml["skills"]["programming"]

    # 3. Text/Markdown format
    text_sample = """
    Bob Wilson
    bob.wilson@example.com | (+84) 987654321 | github.com/bobwilson
    
    Objective:
    Software developer with focus on Python and PostgreSQL.
    
    Skills:
    Python, TypeScript, FastAPI, PostgreSQL, Redis, Docker
    """
    parsed_text = CandidateProfileParser.parse_raw_file("resume.txt", text_sample.encode("utf-8"))
    assert parsed_text["candidate"]["name"] == "Bob Wilson"
    assert parsed_text["candidate"]["email"] == "bob.wilson@example.com"
    assert "Python" in parsed_text["skills"]["programming"]


@pytest.mark.asyncio
async def test_upload_resume_endpoint_yaml(test_client: AsyncClient):
    """Kiểm tra upload file YAML vào endpoint POST /api/v1/profile/upload-resume."""
    headers = {"X-Internal-Secret": settings.INTERNAL_API_SECRET}
    yaml_content = """
    candidate:
      name: "Tran Van B"
      headline: "Data Engineer Intern"
      email: "tranvanb@example.com"
      phone: "(+84) 912345678"
      location: "Ho Chi Minh City"
    skills:
      programming:
        - "Python"
        - "SQL"
      tools_databases:
        - "PostgreSQL"
        - "Redis"
    projects:
      - name: "ETL Pipeline Demo"
        role: "Lead Developer"
        summary: "Automated data pipeline using Python and Postgres"
    """
    files = {
        "file": ("candidate-profile.yaml", io.BytesIO(yaml_content.encode("utf-8")), "application/x-yaml")
    }

    res = await test_client.post("/api/v1/profile/upload-resume", headers=headers, files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["full_name"] == "Tran Van B"
    assert data["skills_count"] >= 2
    assert data["projects_count"] >= 1

    # Verify profile endpoint returns updated candidate
    get_res = await test_client.get("/api/v1/profile", headers=headers)
    assert get_res.status_code == 200
    profile = get_res.json()
    assert profile["full_name"] == "Tran Van B"
    assert profile["email"] == "tranvanb@example.com"


@pytest.mark.asyncio
async def test_upload_resume_endpoint_latex(test_client: AsyncClient):
    """Kiểm tra upload file LaTeX .tex vào endpoint POST /api/v1/profile/upload-resume."""
    headers = {"X-Internal-Secret": settings.INTERNAL_API_SECRET}
    latex_content = r"""
    \documentclass{article}
    \begin{document}
    {\huge \textbf{Le Thi C}} \\
    {\Large \textbf{Frontend Engineer}} \\
    \href{mailto:lethic@example.com}{lethic@example.com} \quad
    \faPhone\ (+84) 909123456 \quad
    \faMapMarker\ Da Nang, Vietnam
    \section*{Objective}
    Frontend specialist in React and NextJS.
    \section*{Skills}
    \begin{itemize}
        \item \textbf{Programming:} JavaScript, TypeScript
        \item \textbf{Frameworks:} React, NextJS, Tailwind CSS
    \end{itemize}
    \end{document}
    """
    files = {
        "file": ("master-resume.tex", io.BytesIO(latex_content.encode("utf-8")), "application/x-tex")
    }

    res = await test_client.post("/api/v1/profile/upload-resume", headers=headers, files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["full_name"] == "Le Thi C"
    assert data["skills_count"] >= 2


@pytest.mark.asyncio
async def test_upload_empty_file_fails(test_client: AsyncClient):
    """Kiểm tra upload file rỗng bị trả về lỗi 400 Bad Request."""
    headers = {"X-Internal-Secret": settings.INTERNAL_API_SECRET}
    files = {
        "file": ("empty.yaml", io.BytesIO(b""), "application/x-yaml")
    }
    res = await test_client.post("/api/v1/profile/upload-resume", headers=headers, files=files)
    assert res.status_code == 400
