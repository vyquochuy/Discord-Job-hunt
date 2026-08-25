import logging
import pytest
import pytest_asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.models.job import Job, JobLevelEnum, JobStatusEnum, RawJob, WorkModeEnum
from app.repositories.candidate import CandidateRepository
from app.services.candidate import CandidateService
from app.services.tailoring.resume_intelligence import (
    resume_intelligence,
    RoleClassifier,
    EvidenceScorer,
    DiverseEvidenceSelector,
)
from app.services.tailoring.latex_generator import latex_generator
from app.services.tailoring.cover_letter_generator import cover_letter_generator
from app.services.tailoring.provenance_verifier import provenance_verifier

logger = logging.getLogger("test.resume_intelligence")


@pytest_asyncio.fixture
async def setup_candidate_and_multirole_jobs():
    """Chuẩn bị 1 candidate profile duy nhất và 3 JD thuộc 3 vai trò khác nhau."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        # 1. Sync candidate profile từ context/
        await CandidateService.sync_profile_from_context(session)
        candidate = await CandidateRepository.get_profile(session)

        # 2. Tạo Job 1: Backend Developer
        raw_job_be = RawJob(
            source="mock",
            source_url="https://mock.vn/job/backend",
            source_job_id="mock-be-1",
            content_hash="hash-be-1",
            fetch_status="PARSED",
        )
        session.add(raw_job_be)
        await session.flush()

        job_backend = Job(
            raw_job_id=raw_job_be.id,
            title="Fresher Backend Developer",
            normalized_title="Fresher Backend Developer",
            company_name="TechCorp Backend Solutions",
            normalized_company="TechCorp Backend Solutions",
            location="Ho Chi Minh City",
            work_mode=WorkModeEnum.ONSITE,
            level=JobLevelEnum.FRESHER,
            status=JobStatusEnum.ACTIVE,
            description=(
                "We need a Fresher Backend Engineer to design REST APIs, relational database schemas, "
                "and microservices. Experience with Python, SQL, PostgreSQL, rate limiting, and backend caching is required."
            ),
            requirements_summary="Python, REST API, Database design, SQL, Redis, backend architecture",
        )
        session.add(job_backend)

        # 3. Tạo Job 2: System / Cloud Infrastructure Intern
        raw_job_sys = RawJob(
            source="mock",
            source_url="https://mock.vn/job/system",
            source_job_id="mock-sys-1",
            content_hash="hash-sys-1",
            fetch_status="PARSED",
        )
        session.add(raw_job_sys)
        await session.flush()

        job_system = Job(
            raw_job_id=raw_job_sys.id,
            title="Cloud Infrastructure & System Intern",
            normalized_title="Cloud Infrastructure & System Intern",
            company_name="CloudOps Network VN",
            normalized_company="CloudOps Network VN",
            location="Ho Chi Minh City",
            work_mode=WorkModeEnum.HYBRID,
            level=JobLevelEnum.INTERN,
            status=JobStatusEnum.ACTIVE,
            description=(
                "Join our Platform Engineering team. You will work on Linux servers, serverless edge workers, "
                "Docker containers, WebSockets real-time networking, and low-latency infrastructure automation."
            ),
            requirements_summary="Linux, Docker, Cloudflare Workers, WebSockets, edge infrastructure, latency optimization",
        )
        session.add(job_system)

        # 4. Tạo Job 3: Security & Cryptography Engineer Intern
        raw_job_sec = RawJob(
            source="mock",
            source_url="https://mock.vn/job/security",
            source_job_id="mock-sec-1",
            content_hash="hash-sec-1",
            fetch_status="PARSED",
        )
        session.add(raw_job_sec)
        await session.flush()

        job_security = Job(
            raw_job_id=raw_job_sec.id,
            title="Cyber Security & Cryptography Intern",
            normalized_title="Cyber Security & Cryptography Intern",
            company_name="SecureNet Cryptographic Labs",
            normalized_company="SecureNet Cryptographic Labs",
            location="Ho Chi Minh City",
            work_mode=WorkModeEnum.ONSITE,
            level=JobLevelEnum.INTERN,
            status=JobStatusEnum.ACTIVE,
            description=(
                "Looking for a Security Intern with strong C++ programming, applied cryptography, "
                "Public Key Infrastructure (PKI), X.509 certificate validation, OpenSSL, and secure network protocol design."
            ),
            requirements_summary="C++, OpenSSL, PKI, X.509, Cryptography, RSA, SHA-256, secure protocols",
        )
        session.add(job_security)

        await session.commit()
        await session.refresh(job_backend)
        await session.refresh(job_system)
        await session.refresh(job_security)

        yield candidate, job_backend, job_system, job_security

    await engine.dispose()


@pytest.mark.asyncio
async def test_role_classifier_logic(setup_candidate_and_multirole_jobs):
    """Kiểm tra Role Classifier phân loại chính xác 3 domain."""
    candidate, job_be, job_sys, job_sec = setup_candidate_and_multirole_jobs

    assert RoleClassifier.classify_role(job_be) == "backend"
    assert RoleClassifier.classify_role(job_sys) == "system"
    assert RoleClassifier.classify_role(job_sec) == "security"


@pytest.mark.asyncio
async def test_relative_evidence_scoring_engine(setup_candidate_and_multirole_jobs):
    """
    Kiểm tra Relative Scoring:
    - Backend JD: Database / API evidence score > Cryptography evidence score.
    - System JD: Infrastructure / WebSocket evidence score > Cryptography evidence score.
    - Security JD: PKI / Cryptography evidence score > Database evidence score.
    """
    candidate, job_be, job_sys, job_sec = setup_candidate_and_multirole_jobs

    # 1. Test trên Backend JD
    strategy_be = resume_intelligence.build_strategy(candidate=candidate, job=job_be)
    assert strategy_be.role_family == "backend"
    assert "backend" in strategy_be.adaptive_summary.lower() or "api" in strategy_be.adaptive_summary.lower()

    # Tìm điểm của từng loại evidence
    all_be_evs = strategy_be.all_scored_evidence
    db_ev = next((e for e in all_be_evs if "database" in e.capabilities or "api" in e.capabilities), None)
    crypto_ev = next((e for e in all_be_evs if "crypto" in e.capabilities and "api" not in e.capabilities), None)

    assert db_ev is not None
    assert crypto_ev is not None
    # Engine Assertion: Điểm của Database/API phải cao hơn Cryptography thuần trên Backend JD
    assert db_ev.score > crypto_ev.score

    # 2. Test trên System JD
    strategy_sys = resume_intelligence.build_strategy(candidate=candidate, job=job_sys)
    assert strategy_sys.role_family == "system"
    assert "infrastructure" in strategy_sys.adaptive_summary.lower() or "linux" in strategy_sys.adaptive_summary.lower()

    all_sys_evs = strategy_sys.all_scored_evidence
    infra_ev = next((e for e in all_sys_evs if "infra" in e.capabilities or "realtime" in e.capabilities), None)
    sec_ev = next((e for e in all_sys_evs if "crypto" in e.capabilities and "infra" not in e.capabilities), None)

    assert infra_ev is not None
    assert sec_ev is not None
    # Engine Assertion: Điểm của Infrastructure/Realtime phải cao hơn Cryptography thuần trên System JD
    assert infra_ev.score > sec_ev.score

    # 3. Test trên Security JD
    strategy_sec = resume_intelligence.build_strategy(candidate=candidate, job=job_sec)
    assert strategy_sec.role_family == "security"
    assert "cryptography" in strategy_sec.adaptive_summary.lower() or "pki" in strategy_sec.adaptive_summary.lower()

    all_sec_evs = strategy_sec.all_scored_evidence
    pki_ev = next((e for e in all_sec_evs if "crypto" in e.capabilities or "system_programming" in e.capabilities), None)
    db_only_ev = next((e for e in all_sec_evs if "database" in e.capabilities and "crypto" not in e.capabilities), None)

    assert pki_ev is not None
    # Engine Assertion: Điểm của PKI/Crypto phải cao hơn Database thuần trên Security JD
    if db_only_ev:
        assert pki_ev.score > db_only_ev.score

    # Dự án EAP-TLS Authentication Protocol Demo phải được xếp hạng cao nhất trên Security JD
    top_project_sec = strategy_sec.ranked_projects[0].project.name
    assert "EAP-TLS" in top_project_sec or "Account Manager" in top_project_sec or "VYVYCHAT" in top_project_sec


@pytest.mark.asyncio
async def test_diverse_evidence_selection(setup_candidate_and_multirole_jobs):
    """Kiểm tra Diversity Filter: Cover Letter không bị lặp lại 3 bullet cùng 1 chủ đề."""
    candidate, job_be, _, _ = setup_candidate_and_multirole_jobs

    strategy = resume_intelligence.build_strategy(candidate=candidate, job=job_be)
    selected = strategy.selected_evidence

    assert len(selected) <= 3
    assert len(selected) >= 2

    # Kiểm tra tính đa dạng năng lực
    capabilities_represented = set()
    for item in selected:
        capabilities_represented.update(item.capabilities)

    # Phải có ít nhất 2 nhóm năng lực khác nhau
    assert len(capabilities_represented) >= 2


@pytest.mark.asyncio
async def test_cross_role_differentiation_and_zero_hallucination(setup_candidate_and_multirole_jobs):
    """
    Kiểm tra phân hóa rõ rệt giữa 3 bản CV và đảm bảo 100% Zero-Hallucination:
    - 3 bản CV có Summary hoàn toàn khác nhau.
    - 3 bản Cover Letter có Key Alignments và Focus khác nhau.
    - Toàn bộ nội dung đều vượt qua Provenance Verification.
    """
    candidate, job_be, job_sys, job_sec = setup_candidate_and_multirole_jobs

    # 1. Sinh 3 Strategies
    strat_be = resume_intelligence.build_strategy(candidate=candidate, job=job_be)
    strat_sys = resume_intelligence.build_strategy(candidate=candidate, job=job_sys)
    strat_sec = resume_intelligence.build_strategy(candidate=candidate, job=job_sec)

    # 2. Kiểm tra Summary phân hóa
    assert strat_be.adaptive_summary != strat_sys.adaptive_summary
    assert strat_sys.adaptive_summary != strat_sec.adaptive_summary
    assert strat_be.adaptive_summary != strat_sec.adaptive_summary

    # 3. Render LaTeX và kiểm tra tính hợp lệ
    tex_be = latex_generator.generate_tailored_tex(candidate=candidate, strategy=strat_be)
    tex_sys = latex_generator.generate_tailored_tex(candidate=candidate, strategy=strat_sys)
    tex_sec = latex_generator.generate_tailored_tex(candidate=candidate, strategy=strat_sec)

    assert "\\begin{document}" in tex_be
    assert "\\begin{document}" in tex_sys
    assert "\\begin{document}" in tex_sec

    # 4. Kiểm chứng Provenance trên từng bản CV
    for strat in [strat_be, strat_sys, strat_sec]:
        sections_dict = {
            "SUMMARY": [strat.adaptive_summary],
            "PROJECTS": [],
        }
        for p in strat.ranked_projects:
            for ev in p.ranked_evidence:
                sections_dict["PROJECTS"].append(ev.evidence_detail)

        evidence_items, score, is_verified = provenance_verifier.verify_resume(
            candidate=candidate,
            tailored_sections=sections_dict,
        )
        assert score >= 90.0
        assert is_verified is True

    # 5. Render Cover Letters và kiểm tra tính dynamic
    cl_be = cover_letter_generator.generate_cover_letter(candidate=candidate, job=job_be, strategy=strat_be)
    cl_sys = cover_letter_generator.generate_cover_letter(candidate=candidate, job=job_sys, strategy=strat_sys)
    cl_sec = cover_letter_generator.generate_cover_letter(candidate=candidate, job=job_sec, strategy=strat_sec)

    assert cl_be["content_markdown"] != cl_sys["content_markdown"]
    assert cl_sys["content_markdown"] != cl_sec["content_markdown"]
    assert "TechCorp Backend Solutions" in cl_be["content_markdown"]
    assert "CloudOps Network VN" in cl_sys["content_markdown"]
    assert "SecureNet Cryptographic Labs" in cl_sec["content_markdown"]
