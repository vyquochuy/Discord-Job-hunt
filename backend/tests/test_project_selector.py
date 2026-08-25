import logging
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.models.candidate import Candidate, CandidateProject
from app.models.job import Job, JobLevelEnum, JobStatusEnum, RawJob, WorkModeEnum
from app.repositories.candidate import CandidateRepository
from app.services.candidate import CandidateService
from app.services.tailoring.project_selector import (
    LayoutBudget,
    ProjectSelectionResult,
    project_selector,
)
from app.services.tailoring.resume_intelligence import (
    EvidenceScorer,
    RoleClassifier,
    ScoredEvidence,
    ScoredProject,
    resume_intelligence,
)

logger = logging.getLogger("test.project_selector")


@pytest_asyncio.fixture
async def setup_candidate_and_test_jobs():
    """Chuẩn bị candidate profile thực tế và các JD mẫu cho test suite."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        await CandidateService.sync_profile_from_context(session)
        candidate = await CandidateRepository.get_profile(session)

        # 1. Backend JD
        job_backend = Job(
            title="Senior Backend Developer (Python / PostgreSQL)",
            normalized_title="Backend Developer",
            company_name="VNG Corp",
            description="Seeking Backend Engineer to build high-scale REST APIs, PostgreSQL data models, Redis caching, microservices, and rate limiting.",
            requirements_summary="Python, FastAPI, PostgreSQL, Redis, RESTful API, Docker",
            work_mode=WorkModeEnum.ONSITE,
            level=JobLevelEnum.SENIOR,
            status=JobStatusEnum.ACTIVE,
        )

        # 2. Security JD
        job_security = Job(
            title="Cyber Security & Cryptography Engineer",
            normalized_title="Security Engineer",
            company_name="SecureNet Labs",
            description="Applied cryptography, PKI X.509 certificate validation, OpenSSL, EAP-TLS authentication protocol simulation, AES-GCM, Argon2id, zero-knowledge.",
            requirements_summary="C++, OpenSSL, PKI, X.509, Cryptography, RSA, SHA-256",
            work_mode=WorkModeEnum.HYBRID,
            level=JobLevelEnum.INTERN,
            status=JobStatusEnum.ACTIVE,
        )

        # 3. System / Cloud Infrastructure JD
        job_system = Job(
            title="Cloud Infrastructure & Edge Systems Intern",
            normalized_title="System Intern",
            company_name="Cloudflare Ecosystem Partner",
            description="Developing stateful edge WebSocket services with Cloudflare Workers and Durable Objects, Linux automation, low-latency PoP networking.",
            requirements_summary="Cloudflare Workers, Durable Objects, WebSockets, Linux, Docker, TypeScript",
            work_mode=WorkModeEnum.REMOTE,
            level=JobLevelEnum.INTERN,
            status=JobStatusEnum.ACTIVE,
        )

        yield candidate, job_backend, job_security, job_system

    await engine.dispose()


@pytest.mark.asyncio
async def test_relevant_projects_selected_backend(setup_candidate_and_test_jobs):
    """Test 1: Backend JD tuyển chọn các dự án liên quan backend/API/database, không lấy dự án thừa."""
    candidate, job_backend, _, _ = setup_candidate_and_test_jobs

    strategy = resume_intelligence.build_strategy(candidate=candidate, job=job_backend)
    selected_names = [p.project.name for p in strategy.selected_projects]

    assert len(strategy.selected_projects) <= 3
    assert len(strategy.selected_projects) >= 2

    # AI Job Hunter (Backend/FastAPI/PostgreSQL) phải nằm trong top selected
    assert any("AI Job Hunter" in name for name in selected_names)
    # VYVYCHAT hoặc Account Manager cũng liên quan
    assert any("VYVYCHAT" in name or "Account Manager" in name for name in selected_names)


@pytest.mark.asyncio
async def test_irrelevant_project_rejected():
    """Test 2: Một dự án có relevance cực thấp (< threshold) phải bị loại bỏ dứt khoát."""
    # Tạo mock projects với 1 project hoàn toàn lạc đề
    p_backend = CandidateProject(
        name="AI Job Hunter",
        summary="Backend system for job intelligence",
        technologies=["Python", "FastAPI", "PostgreSQL", "Redis"],
        evidence_points=[
            {"title": "API Engine", "detail": "Built REST APIs with FastAPI and PostgreSQL database."}
        ],
    )
    p_irrelevant = CandidateProject(
        name="Sokoban 2D Retro Game",
        summary="Simple 2D game in Pascal for high school project",
        technologies=["Pascal", "Turbo Pascal"],
        evidence_points=[
            {"title": "Game Logic", "detail": "Implemented 2D grid movement and box pushing logic."}
        ],
    )

    job_backend = Job(
        title="Senior Python Backend Developer",
        description="High throughput API services with FastAPI, PostgreSQL, Redis, Docker.",
        requirements_summary="FastAPI, PostgreSQL, Redis",
        work_mode=WorkModeEnum.ONSITE,
        level=JobLevelEnum.SENIOR,
        status=JobStatusEnum.ACTIVE,
    )

    scored_projects = [
        ScoredProject(
            project=p_backend,
            project_score=0.92,
            ranked_evidence=[
                ScoredEvidence(
                    project_name="AI Job Hunter",
                    evidence_title="API Engine",
                    evidence_detail="Built REST APIs with FastAPI and PostgreSQL database.",
                    technologies=["Python", "FastAPI", "PostgreSQL"],
                    score=0.92,
                    capabilities=["api", "database"],
                )
            ],
        ),
        ScoredProject(
            project=p_irrelevant,
            project_score=0.20,
            ranked_evidence=[
                ScoredEvidence(
                    project_name="Sokoban 2D Retro Game",
                    evidence_title="Game Logic",
                    evidence_detail="Implemented 2D grid movement and box pushing logic.",
                    technologies=["Pascal"],
                    score=0.20,
                    capabilities=["general"],
                )
            ],
        ),
    ]

    budget = LayoutBudget(min_projects=1, max_projects=3, min_project_threshold=0.50)
    result = project_selector.select_projects(
        candidate_projects=scored_projects,
        job=job_backend,
        role_family="backend",
        matched_skills=["Python", "FastAPI", "PostgreSQL", "Redis"],
        layout_budget=budget,
    )

    selected_names = [sp.project.name for sp in result.selected_projects]
    rejected_names = [sp.project.name for sp in result.rejected_projects]

    assert "AI Job Hunter" in selected_names
    assert "Sokoban 2D Retro Game" in rejected_names
    assert "Sokoban 2D Retro Game" not in selected_names


@pytest.mark.asyncio
async def test_diversity_selection_preference():
    """Test 3: Khi có 3 dự án trùng lặp API/DB và 1 dự án Security/Crypto, selector ưu tiên Security để tăng diversity."""
    p1 = CandidateProject(
        name="API Project 1",
        technologies=["Python", "FastAPI", "PostgreSQL"],
        evidence_points=[{"title": "API", "detail": "CRUD REST API endpoints."}],
    )
    p2 = CandidateProject(
        name="API Project 2",
        technologies=["Python", "FastAPI", "PostgreSQL"],
        evidence_points=[{"title": "API", "detail": "CRUD REST API endpoints."}],
    )
    p3 = CandidateProject(
        name="API Project 3",
        technologies=["Python", "FastAPI", "PostgreSQL"],
        evidence_points=[{"title": "API", "detail": "CRUD REST API endpoints."}],
    )
    p_sec = CandidateProject(
        name="Security Vault",
        technologies=["TypeScript", "Argon2id", "AES-256", "Zero-Knowledge"],
        evidence_points=[{"title": "Crypto", "detail": "Zero-Knowledge client-side encryption and Argon2id hashing."}],
    )

    job = Job(
        title="Fullstack / Backend Developer",
        description="Backend development with APIs, databases, authentication, and security.",
        requirements_summary="Python, API, Database, Security, Cryptography",
        work_mode=WorkModeEnum.ONSITE,
        level=JobLevelEnum.JUNIOR,
        status=JobStatusEnum.ACTIVE,
    )

    scored_projects = [
        ScoredProject(
            project=p1,
            project_score=0.88,
            ranked_evidence=[ScoredEvidence("API Project 1", "API", "CRUD REST API.", ["Python"], 0.88, ["api", "database"])],
        ),
        ScoredProject(
            project=p2,
            project_score=0.86,
            ranked_evidence=[ScoredEvidence("API Project 2", "API", "CRUD REST API.", ["Python"], 0.86, ["api", "database"])],
        ),
        ScoredProject(
            project=p3,
            project_score=0.85,
            ranked_evidence=[ScoredEvidence("API Project 3", "API", "CRUD REST API.", ["Python"], 0.85, ["api", "database"])],
        ),
        ScoredProject(
            project=p_sec,
            project_score=0.82,
            ranked_evidence=[ScoredEvidence("Security Vault", "Crypto", "Zero-Knowledge encryption.", ["Argon2id"], 0.82, ["crypto", "security"])],
        ),
    ]

    budget = LayoutBudget(min_projects=2, max_projects=2)
    result = project_selector.select_projects(
        candidate_projects=scored_projects,
        job=job,
        role_family="backend",
        matched_skills=["Python", "API", "Security"],
        layout_budget=budget,
    )

    selected_names = [sp.project.name for sp in result.selected_projects]
    assert len(selected_names) == 2
    # P1 (top score) và Security Vault (diversity bonus) phải được chọn
    assert "API Project 1" in selected_names
    assert "Security Vault" in selected_names


@pytest.mark.asyncio
async def test_specialist_security_jd(setup_candidate_and_test_jobs):
    """Test 4: Security JD ưu tiên các dự án Cryptography, PKI, EAP-TLS; các dự án thuần UI/API xếp sau."""
    candidate, _, job_security, _ = setup_candidate_and_test_jobs

    strategy = resume_intelligence.build_strategy(candidate=candidate, job=job_security)
    selected_names = [p.project.name for p in strategy.selected_projects]

    # EAP-TLS và Account Manager (Zero-Knowledge) phải được ưu tiên hàng đầu
    assert any("EAP-TLS" in name for name in selected_names)
    assert any("Account Manager" in name or "VYVYCHAT" in name for name in selected_names)


@pytest.mark.asyncio
async def test_small_candidate_set_graceful():
    """Test 5: Khi candidate chỉ có 1 hoặc 2 projects phù hợp, hệ thống xuất 1-2 projects mà không báo lỗi."""
    p_only = CandidateProject(
        name="Solo Project",
        technologies=["Python", "FastAPI"],
        evidence_points=[{"title": "Core", "detail": "Single high-quality backend project."}],
    )
    job = Job(
        title="Python Developer",
        description="Python backend role.",
        requirements_summary="Python",
        work_mode=WorkModeEnum.REMOTE,
        level=JobLevelEnum.FRESHER,
        status=JobStatusEnum.ACTIVE,
    )
    scored_projects = [
        ScoredProject(
            project=p_only,
            project_score=0.90,
            ranked_evidence=[ScoredEvidence("Solo Project", "Core", "Single backend project.", ["Python"], 0.90, ["api"])],
        )
    ]

    budget = LayoutBudget(min_projects=1, max_projects=3)
    result = project_selector.select_projects(
        candidate_projects=scored_projects,
        job=job,
        role_family="backend",
        matched_skills=["Python"],
        layout_budget=budget,
    )

    assert len(result.selected_projects) == 1
    assert result.selected_projects[0].project.name == "Solo Project"
    assert len(result.rejected_projects) == 0


@pytest.mark.asyncio
async def test_selection_determinism(setup_candidate_and_test_jobs):
    """Test 6: Chạy selector nhiều lần với cùng input phải cho 100% kết quả và thứ tự giống nhau."""
    candidate, job_backend, _, _ = setup_candidate_and_test_jobs

    strat1 = resume_intelligence.build_strategy(candidate=candidate, job=job_backend)
    strat2 = resume_intelligence.build_strategy(candidate=candidate, job=job_backend)

    names1 = [p.project.name for p in strat1.selected_projects]
    names2 = [p.project.name for p in strat2.selected_projects]

    assert names1 == names2
    assert [p.project_score for p in strat1.selected_projects] == [p.project_score for p in strat2.selected_projects]


@pytest.mark.asyncio
async def test_no_hallucinated_projects(setup_candidate_and_test_jobs):
    """Test 7: Tập selected projects luôn là tập con chính xác của candidate projects."""
    candidate, job_backend, job_sec, job_sys = setup_candidate_and_test_jobs
    candidate_proj_names = {p.name for p in candidate.projects}

    for job in [job_backend, job_sec, job_sys]:
        strat = resume_intelligence.build_strategy(candidate=candidate, job=job)
        selected_names = {p.project.name for p in strat.selected_projects}
        assert selected_names.issubset(candidate_proj_names)


@pytest.mark.asyncio
async def test_bullet_pruning_and_layout_budget(setup_candidate_and_test_jobs):
    """Test 8: Cắt tỉa bullets không quá giới hạn LayoutBudget toàn CV."""
    candidate, job_backend, _, _ = setup_candidate_and_test_jobs

    strategy = resume_intelligence.build_strategy(candidate=candidate, job=job_backend)

    total_bullets = sum(len(p.ranked_evidence) for p in strategy.selected_projects)
    # Tổng bullets toàn CV không vượt quá max_total_bullets (7)
    assert total_bullets <= 7
    # Mỗi project có ít nhất 1 và không quá 3 bullets
    for p in strategy.selected_projects:
        assert len(p.ranked_evidence) >= 1
        assert len(p.ranked_evidence) <= 3


@pytest.mark.asyncio
async def test_explainability_metadata(setup_candidate_and_test_jobs):
    """Test 9: ProjectSelectionResult sinh đầy đủ metadata scores và reasons giải thích minh bạch."""
    candidate, job_backend, _, _ = setup_candidate_and_test_jobs

    strategy = resume_intelligence.build_strategy(candidate=candidate, job=job_backend)
    sel_res: ProjectSelectionResult = strategy.project_selection_result

    assert sel_res is not None
    assert len(sel_res.scores) > 0
    assert len(sel_res.reasons) > 0

    for name, reason in sel_res.reasons.items():
        assert len(reason) > 10
        assert "Được chọn" in reason or "Loại bỏ" in reason
