import logging
import pytest
import pytest_asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.models.job import Job, JobLevelEnum, JobStatusEnum, RawJob, WorkModeEnum
from app.repositories.candidate import CandidateRepository
from app.services.candidate import CandidateService
from app.services.tailoring.fact_graph import fact_graph_builder
from app.services.tailoring.jd_capability_analyzer import jd_capability_analyzer
from app.services.tailoring.resume_intelligence import (
    resume_intelligence,
    RoleClassifier,
    EvidenceScorer,
    DiverseEvidenceSelector,
)
from app.services.tailoring.project_selector import project_selector
from app.services.tailoring.latex_generator import latex_generator
from app.services.tailoring.provenance_verifier import provenance_verifier
from app.services.tailoring.resume_service import ResumeTailorService

logger = logging.getLogger("test.jd_agnostic_tailoring")


@pytest_asyncio.fixture
async def setup_test_db():
    """Tạo database test in-memory và nạp hồ sơ ứng viên gốc."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        await CandidateService.sync_profile_from_context(session)
        candidate = await CandidateRepository.get_profile(session)
        yield session, candidate

    await engine.dispose()


async def create_mock_job(session: AsyncSession, title: str, description: str, reqs: str, level=JobLevelEnum.INTERN) -> Job:
    raw_job = RawJob(
        source="mock",
        source_url=f"https://mock.vn/job/{uuid.uuid4()}",
        source_job_id=f"mock-{uuid.uuid4()}",
        content_hash=f"hash-{uuid.uuid4()}",
        fetch_status="PARSED",
    )
    session.add(raw_job)
    await session.flush()
    
    job = Job(
        raw_job_id=raw_job.id,
        title=title,
        normalized_title=title,
        company_name="Test Enterprise Inc",
        normalized_company="Test Enterprise Inc",
        location="Ho Chi Minh City",
        work_mode=WorkModeEnum.HYBRID,
        level=level,
        status=JobStatusEnum.ACTIVE,
        description=description,
        requirements_summary=reqs,
    )
    session.add(job)
    await session.flush()
    return job


@pytest.mark.asyncio
async def test_scenario_1_backend_fastapi_job(setup_test_db):
    """Kịch bản 1: Python / FastAPI Backend Engineer."""
    session, candidate = setup_test_db
    job = await create_mock_job(
        session,
        title="Backend Developer (Python / FastAPI)",
        description="We are building distributed microservices, REST APIs, and database schemas with FastAPI, PostgreSQL, and Redis caching.",
        reqs="Python, FastAPI, PostgreSQL, Redis, REST API, Database design, SQL",
    )
    await session.commit()
    await session.refresh(job)

    strategy = resume_intelligence.build_strategy(candidate=candidate, job=job)
    assert strategy.role_family == "backend"
    selected_names = [p.project.name for p in strategy.selected_projects]
    assert any("AI Job Hunter" in n or "VYVYCHAT" in n or "Account Manager" in n for n in selected_names)
    assert any(s in strategy.priority_skills[:5] for s in ["Python", "FastAPI", "SQL", "PostgreSQL", "Redis"])


@pytest.mark.asyncio
async def test_scenario_2_cybersecurity_cryptography_job(setup_test_db):
    """Kịch bản 2: Cybersecurity & Cryptography Engineer."""
    session, candidate = setup_test_db
    job = await create_mock_job(
        session,
        title="Cybersecurity & Cryptography Engineer Intern",
        description="Develop Public Key Infrastructure (PKI), validate X.509 certificates, implement EAP-TLS protocols, and secure data using OpenSSL and modern C++.",
        reqs="C++, OpenSSL, PKI, X.509, Cryptography, RSA, SHA-256, Zero-Knowledge",
    )
    await session.commit()
    await session.refresh(job)

    strategy = resume_intelligence.build_strategy(candidate=candidate, job=job)
    assert strategy.role_family == "security"
    selected_names = [p.project.name for p in strategy.selected_projects]
    assert any("EAP-TLS" in n or "Account Manager" in n for n in selected_names)
    assert any(s in strategy.priority_skills[:5] for s in ["OpenSSL", "X.509 PKI", "C++", "Zero-Knowledge Architecture"])


@pytest.mark.asyncio
async def test_scenario_3_modern_cpp_systems_job(setup_test_db):
    """Kịch bản 3: Modern C++ Systems Engineer."""
    session, candidate = setup_test_db
    job = await create_mock_job(
        session,
        title="Systems Software Engineer (C++17)",
        description="Design and implement system-level network protocol emulations in C++17 with multi-entity architecture, memory management, and socket communications.",
        reqs="C++17, OOP, Protocol design, Linux, OpenSSL, Socket programming, System design",
    )
    await session.commit()
    await session.refresh(job)

    strategy = resume_intelligence.build_strategy(candidate=candidate, job=job)
    selected_names = [p.project.name for p in strategy.selected_projects]
    assert any("EAP-TLS" in n for n in selected_names)
    assert "C++" in strategy.priority_skills[:5]


@pytest.mark.asyncio
async def test_scenario_4_frontend_react_job(setup_test_db):
    """Kịch bản 4: Frontend / React Web Developer."""
    session, candidate = setup_test_db
    job = await create_mock_job(
        session,
        title="Frontend Web Developer (React / TypeScript)",
        description="Build responsive and accessible real-time user interfaces with React, TypeScript, Tailwind CSS, and WebSockets.",
        reqs="React, TypeScript, Tailwind CSS, UI, WebSockets, HTML5, CSS3",
    )
    await session.commit()
    await session.refresh(job)

    strategy = resume_intelligence.build_strategy(candidate=candidate, job=job)
    selected_names = [p.project.name for p in strategy.selected_projects]
    assert any("VYVYCHAT" in n for n in selected_names)
    assert any(s in strategy.priority_skills[:5] for s in ["React", "TypeScript", "Tailwind CSS", "JavaScript"])


@pytest.mark.asyncio
async def test_scenario_5_mobile_flutter_job(setup_test_db):
    """Kịch bản 5: Mobile Developer (Flutter / Dart)."""
    session, candidate = setup_test_db
    job = await create_mock_job(
        session,
        title="Mobile App Developer (Flutter / Dart)",
        description="Develop cross-platform mobile apps for Android/iOS with Flutter, Dart, offline local storage, and secure keystore synchronization.",
        reqs="Flutter, Dart, Mobile app, Keystore, Offline storage, REST API",
    )
    await session.commit()
    await session.refresh(job)

    strategy = resume_intelligence.build_strategy(candidate=candidate, job=job)
    selected_names = [p.project.name for p in strategy.selected_projects]
    assert any("Account Manager" in n for n in selected_names)
    assert any(s in strategy.priority_skills[:5] for s in ["Flutter", "Dart"])


@pytest.mark.asyncio
async def test_scenario_6_hybrid_fintech_backend_security_job(setup_test_db):
    """Kịch bản 6: Hybrid Backend + Security (Fintech Core API)."""
    session, candidate = setup_test_db
    job = await create_mock_job(
        session,
        title="Fintech Core Backend & Security Engineer",
        description="Design high-throughput banking REST APIs with SQLite/PostgreSQL, token-bucket rate limiting, anti-enumeration, and zero-knowledge data modeling.",
        reqs="Backend, REST APIs, Rate limiting, PostgreSQL, SQLite, Zero-knowledge, Cryptography, Anti-enumeration",
    )
    await session.commit()
    await session.refresh(job)

    strategy = resume_intelligence.build_strategy(candidate=candidate, job=job)
    selected_names = [p.project.name for p in strategy.selected_projects]
    assert any("Account Manager" in n or "VYVYCHAT" in n or "AI Job Hunter" in n for n in selected_names)
    assert len(strategy.selected_projects) >= 2


@pytest.mark.asyncio
async def test_scenario_7_general_software_engineer_intern(setup_test_db):
    """Kịch bản 7: General Software Engineer Intern."""
    session, candidate = setup_test_db
    job = await create_mock_job(
        session,
        title="Software Engineer Intern",
        description="Looking for passionate computer science interns with solid foundations in OOP, algorithms, databases, and modern software engineering practices.",
        reqs="OOP, Algorithms, SQL, Git, Linux, Problem-solving, Teamwork",
    )
    await session.commit()
    await session.refresh(job)

    strategy = resume_intelligence.build_strategy(candidate=candidate, job=job)
    assert len(strategy.selected_projects) >= 1
    assert "University of Science" in strategy.adaptive_summary


@pytest.mark.asyncio
async def test_scenario_8_mismatched_role_zero_hallucination(setup_test_db):
    """Kịch bản 8: JD không match (Java Spring Boot 5 năm) -> Không tự bịa Java kinh nghiệm."""
    session, candidate = setup_test_db
    job = await create_mock_job(
        session,
        title="Senior Java Spring Boot Architect",
        description="Require 5+ years of experience architecting enterprise banking platforms in Java 17, Spring Boot, Hibernate, Oracle DB, and Kubernetes.",
        reqs="Java, Spring Boot, Hibernate, Oracle DB, Kubernetes, Enterprise Banking",
        level=JobLevelEnum.SENIOR,
    )
    await session.commit()
    await session.refresh(job)

    strategy = resume_intelligence.build_strategy(candidate=candidate, job=job)
    # Đảm bảo KHÔNG có "Spring Boot" hay "Hibernate" trong kỹ năng được gán cho ứng viên
    assert "Spring Boot" not in strategy.priority_skills
    assert "Hibernate" not in strategy.priority_skills
    assert "Oracle DB" not in strategy.priority_skills


@pytest.mark.asyncio
async def test_scenario_9_unseen_technologies_no_phantom_skills(setup_test_db):
    """Kịch bản 9: JD yêu cầu Rust, Kubernetes, Kafka -> Ứng viên không có -> Không hallucinate."""
    session, candidate = setup_test_db
    job = await create_mock_job(
        session,
        title="Cloud Native Infrastructure Engineer (Rust / K8s)",
        description="Deploy high-throughput microservices using Rust, Apache Kafka, Terraform, and Kubernetes clusters on AWS.",
        reqs="Rust, Kubernetes, Apache Kafka, Terraform, AWS, Docker",
    )
    await session.commit()
    await session.refresh(job)

    strategy = resume_intelligence.build_strategy(candidate=candidate, job=job)
    assert "Rust" not in strategy.priority_skills
    assert "Kubernetes" not in strategy.priority_skills
    assert "Apache Kafka" not in strategy.priority_skills


@pytest.mark.asyncio
async def test_scenario_10_adversarial_metric_injection_grounding(setup_test_db):
    """Kịch bản 10: JD yêu cầu số liệu ảo (quản lý 50 người, tiết kiệm 1M USD) -> Provenance chặn tuyệt đối."""
    session, candidate = setup_test_db
    job = await create_mock_job(
        session,
        title="Engineering Manager (Team of 50, Budget $1M)",
        description="Led an engineering department of 50 developers and cut cloud infrastructure costs by $1,000,000 USD across 5 global regions.",
        reqs="Engineering leadership, 50 people, $1,000,000, Budget management",
        level=JobLevelEnum.SENIOR,
    )
    await session.commit()
    await session.refresh(job)

    tailored = await ResumeTailorService.tailor_resume_for_job(
        session=session,
        job_id=job.id,
        candidate_id=candidate.id,
        force_regenerate=True,
    )

    assert tailored is not None
    assert tailored.provenance_score >= 50.0
    assert "$1,000,000" not in tailored.latex_source
    assert "50 developers" not in tailored.latex_source
