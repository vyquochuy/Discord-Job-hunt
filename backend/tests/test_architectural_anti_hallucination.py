import pytest
import pytest_asyncio
from typing import List, Set
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.models.candidate import Candidate, CandidateProject
from app.models.job import Job, JobLevelEnum, JobStatusEnum, RawJob, WorkModeEnum
from app.repositories.candidate import CandidateRepository
from app.services.candidate import CandidateService
from app.schemas.tailoring_ir import (
    EvidenceBundle,
    EvidenceCategory,
    EvidenceFact,
    GeneratedBullet,
    GeneratedClaimFragment,
    GeneratedProject,
    GeneratedSummary,
    LayoutBudget,
    StructuredResumeDraft,
    TailoringStrategy,
    ValidationViolationType,
)
from app.services.tailoring.alias_registry import alias_registry
from app.services.tailoring.deterministic_composer import deterministic_composer
from app.services.tailoring.evidence_validator import (
    claim_validator,
    unit_regeneration_orchestrator,
)
from app.services.tailoring.fact_graph import evidence_registry
from app.services.tailoring.gemini_resume_writer import resume_semantic_writer
from app.services.tailoring.latex_generator import latex_generator
from app.services.tailoring.resume_intelligence import resume_intelligence


@pytest.fixture
def sample_candidate_with_facts() -> Candidate:
    """Fixture cung cấp Candidate với các EvidenceFact phong phú."""
    cand = Candidate(
        full_name="Vy Quoc Huy",
        headline="Computer Science Student",
        summary="Final-year student specializing in Cyber Security and Distributed Systems.",
        education=[{
            "institution": "VNUHCM - University of Science",
            "field": "Computer Science (Cyber Security)",
            "graduation_year": 2026,
            "gpa": "3.15/4.0",
        }],
    )

    p1 = CandidateProject(
        name="Account Manager: Zero-Knowledge Password Vault",
        summary="Offline-first password manager with encrypted cloud synchronization.",
        technologies=["Flutter", "Dart", "Cloudflare Workers", "Hono", "Hive", "Argon2id", "AES-256-GCM", "Shamir Secret Sharing"],
        evidence_points=[
            {
                "title": "Zero-Knowledge Key Recovery",
                "detail": "Implemented server-side authentication with client-side Argon2id password hashing (t=3, m=64MB) and deterministic fake salts to mitigate user enumeration.",
                "is_core": True,
                "technologies": ["Argon2id", "AES-256-GCM", "Cloudflare Workers"],
            },
            {
                "title": "Serverless Sync API",
                "detail": "Engineered REST APIs on Cloudflare Workers and Hono sustaining 200 req/min rate limit capacity.",
                "is_core": False,
                "technologies": ["Cloudflare Workers", "Hono", "TypeScript"],
            }
        ],
        order=0,
    )

    p2 = CandidateProject(
        name="VYVYCHAT",
        summary="Real-time messaging platform on Cloudflare serverless edge.",
        technologies=["React", "TypeScript", "Tailwind CSS", "Cloudflare Workers", "Durable Objects", "Cloudflare D1", "Cloudflare KV"],
        evidence_points=[
            {
                "title": "Stateful Real-Time Edge",
                "detail": "Engineered a stateful WebSocket layer using Cloudflare Durable Objects managing persistent edge connections with ~45ms latency.",
                "is_core": True,
                "technologies": ["Cloudflare Workers", "Durable Objects", "WebSocket"],
            }
        ],
        order=1,
    )

    cand.projects = [p1, p2]
    return cand


@pytest.fixture
def sample_evidence_bundle(sample_candidate_with_facts) -> EvidenceBundle:
    """Fixture tạo EvidenceBundle chuẩn cho Backend Job."""
    job = Job(
        title="Backend Developer Intern",
        company_name="CloudTech VN",
        description="Looking for Backend Intern with Cloudflare Workers, Hono, REST API, SQLite, and rate limiting.",
        requirements_summary="Cloudflare Workers, Hono, REST API, SQLite, Rate Limiting",
    )
    return resume_intelligence.build_evidence_bundle(
        candidate=sample_candidate_with_facts,
        job=job,
    )


# ============================================================================
# TEST 1: Valid Evidence-Grounded Bullet (Passes Validation)
# ============================================================================

def test_valid_evidence_grounded_bullet_passes(sample_evidence_bundle):
    """
    Test 1: Bullet hợp lệ viện dẫn đúng Evidence ID, công nghệ và metric có thật
    -> Phải PASS hoàn toàn (0 violations).
    """
    valid_bullet = GeneratedBullet(
        text="Engineered REST APIs on Cloudflare Workers and Hono sustaining 200 req/min rate limit capacity.",
        evidence_ids=["project.account_manager__zero_knowledge_password_vault.bullet_2"],
        claims=[
            GeneratedClaimFragment(
                claim="Engineered REST APIs on Cloudflare Workers and Hono",
                evidence_ids=["project.account_manager__zero_knowledge_password_vault.bullet_2"],
            ),
            GeneratedClaimFragment(
                claim="Sustaining 200 req/min rate limit capacity",
                evidence_ids=["project.account_manager__zero_knowledge_password_vault.bullet_2"],
            )
        ]
    )

    violations = claim_validator.validate_bullet(
        bullet=valid_bullet,
        unit_id="test.bullet_1",
        project_name="Account Manager: Zero-Knowledge Password Vault",
        bundle=sample_evidence_bundle,
    )

    assert len(violations) == 0, f"Valid bullet should not have violations: {violations}"


# ============================================================================
# TEST 2: Invented Technology (Detected and Rejected)
# ============================================================================

def test_invented_technology_rejected(sample_evidence_bundle):
    """
    Test 2: Bullet đưa vào công nghệ bịa đặt (Kubernetes / Apache Kafka)
    -> Phải bị bắt lỗi UNSUPPORTED_TECHNOLOGY.
    """
    fake_tech_bullet = GeneratedBullet(
        text="Architected distributed event streaming using Apache Kafka and deployed on Kubernetes clusters.",
        evidence_ids=["project.account_manager__zero_knowledge_password_vault.bullet_2"],
        claims=[
            GeneratedClaimFragment(
                claim="Event streaming with Kafka on Kubernetes",
                evidence_ids=["project.account_manager__zero_knowledge_password_vault.bullet_2"],
            )
        ]
    )

    violations = claim_validator.validate_bullet(
        bullet=fake_tech_bullet,
        unit_id="test.bullet_2",
        project_name="Account Manager: Zero-Knowledge Password Vault",
        bundle=sample_evidence_bundle,
    )

    assert len(violations) > 0
    violation_types = [v.violation_type for v in violations]
    assert ValidationViolationType.UNSUPPORTED_TECHNOLOGY in violation_types


def test_technology_alias_normalization_prevents_false_positives(sample_evidence_bundle):
    """
    Test 2.1: Công nghệ viết theo alias (AES-GCM thay vì AES-256-GCM; Workers thay vì Cloudflare Workers)
    -> Validator thông qua Alias Registry phải NHẬN DIỆN ĐÚNG và KHÔNG báo lỗi sai (Zero False Positive).
    """
    alias_bullet = GeneratedBullet(
        text="Implemented client-side encryption using AES-GCM and Argon2 for secure key management.",
        evidence_ids=["project.account_manager__zero_knowledge_password_vault.bullet_1"],
        claims=[
            GeneratedClaimFragment(
                claim="Encryption using AES-GCM and Argon2",
                evidence_ids=["project.account_manager__zero_knowledge_password_vault.bullet_1"],
            )
        ]
    )

    violations = claim_validator.validate_bullet(
        bullet=alias_bullet,
        unit_id="test.bullet_alias",
        project_name="Account Manager: Zero-Knowledge Password Vault",
        bundle=sample_evidence_bundle,
    )

    # Không được báo lỗi Unsupported Technology cho AES-GCM và Argon2
    tech_violations = [v for v in violations if v.violation_type == ValidationViolationType.UNSUPPORTED_TECHNOLOGY]
    assert len(tech_violations) == 0, f"Alias tech should be normalized and accepted: {tech_violations}"


# ============================================================================
# TEST 3: Invented Metric (Detected and Rejected)
# ============================================================================

def test_invented_metric_rejected(sample_evidence_bundle):
    """
    Test 3: Bullet tự bịa số liệu (% cải thiện hoặc lưu lượng triệu QPS không có trong evidence)
    -> Phải bị bắt lỗi UNSUPPORTED_METRIC.
    """
    fake_metric_bullet = GeneratedBullet(
        text="Optimized database indexing achieving 1000000 QPS throughput and reduced latency by 90%.",
        evidence_ids=["project.account_manager__zero_knowledge_password_vault.bullet_2"],
        claims=[]
    )

    violations = claim_validator.validate_bullet(
        bullet=fake_metric_bullet,
        unit_id="test.bullet_3",
        project_name="Account Manager: Zero-Knowledge Password Vault",
        bundle=sample_evidence_bundle,
    )

    assert len(violations) > 0
    violation_types = [v.violation_type for v in violations]
    assert ValidationViolationType.UNSUPPORTED_METRIC in violation_types


# ============================================================================
# TEST 4: Unsupported JD Requirement (No Fabrication Allowed)
# ============================================================================

def test_unsupported_jd_requirement_not_fabricated(sample_candidate_with_facts):
    """
    Test 4: JD đòi hỏi Cassandra, GraphQL, gRPC mà ứng viên không có
    -> Unsupported requirements phải được nhận diện và nếu xuất hiện trong bullet sẽ bị REJECT.
    """
    job_with_gaps = Job(
        title="Senior Distributed Systems Engineer",
        description="Must have extensive production experience in Apache Cassandra, gRPC, and GraphQL federation.",
        requirements_summary="Cassandra, gRPC, GraphQL",
    )

    bundle = resume_intelligence.build_evidence_bundle(
        candidate=sample_candidate_with_facts,
        job=job_with_gaps,
    )

    # Kiểm tra gap analysis
    assert any("cassandra" in req.lower() or "grpc" in req.lower() for req in bundle.strategy.unsupported_requirements)

    # Thử tạo bullet vi phạm gap
    fabricated_bullet = GeneratedBullet(
        text="Built high-performance RPC services using gRPC and modeled distributed tables in Cassandra.",
        evidence_ids=["project.account_manager__zero_knowledge_password_vault.bullet_2"],
        claims=[]
    )

    violations = claim_validator.validate_bullet(
        bullet=fabricated_bullet,
        unit_id="test.bullet_gap",
        project_name="Account Manager: Zero-Knowledge Password Vault",
        bundle=bundle,
    )

    assert len(violations) > 0
    violation_types = [v.violation_type for v in violations]
    assert (
        ValidationViolationType.UNSUPPORTED_JD_FABRICATION in violation_types
        or ValidationViolationType.UNSUPPORTED_TECHNOLOGY in violation_types
    )


# ============================================================================
# TEST 5: Experience Inflation (Detected and Rejected)
# ============================================================================

def test_experience_inflation_rejected(sample_evidence_bundle):
    """
    Test 5: Bullet tự nâng cấp vai trò sinh viên/coursework thành 'managed team of 50'
    -> Phải bị bắt lỗi EXPERIENCE_INFLATION.
    """
    inflated_bullet = GeneratedBullet(
        text="Led an engineering team of 50 senior developers and maintained 99.999% uptime on production enterprise cluster.",
        evidence_ids=["project.account_manager__zero_knowledge_password_vault.bullet_2"],
        claims=[]
    )

    violations = claim_validator.validate_bullet(
        bullet=inflated_bullet,
        unit_id="test.bullet_inflation",
        project_name="Account Manager: Zero-Knowledge Password Vault",
        bundle=sample_evidence_bundle,
    )

    assert len(violations) > 0
    violation_types = [v.violation_type for v in violations]
    assert ValidationViolationType.EXPERIENCE_INFLATION in violation_types


# ============================================================================
# TEST 6: Invalid Evidence ID (Rejected)
# ============================================================================

def test_invalid_evidence_id_rejected(sample_evidence_bundle):
    """
    Test 6: Bullet viện dẫn Evidence ID ma ('project.fake.bullet_999')
    -> Phải bị bắt lỗi INVALID_EVIDENCE_ID.
    """
    invalid_id_bullet = GeneratedBullet(
        text="Developed secure authentication workflow.",
        evidence_ids=["project.non_existent_vault.fake_bullet_999"],
        claims=[]
    )

    violations = claim_validator.validate_bullet(
        bullet=invalid_id_bullet,
        unit_id="test.bullet_invalid_id",
        project_name="Account Manager: Zero-Knowledge Password Vault",
        bundle=sample_evidence_bundle,
    )

    assert len(violations) > 0
    violation_types = [v.violation_type for v in violations]
    assert ValidationViolationType.INVALID_EVIDENCE_ID in violation_types


# ============================================================================
# TEST 7: Unit-Level Regeneration & Locking
# ============================================================================

@pytest.mark.asyncio
async def test_unit_regeneration_orchestrator_locks_valid_units(sample_evidence_bundle):
    """
    Test 7: Vòng lặp Regeneration:
    - Bullet 1 HỢP LỆ -> Phải được KHÓA (LOCKED) và giữ nguyên.
    - Bullet 2 VI PHẠM (invented tech) -> Phải được sửa lại thành hợp lệ.
    - Kết quả cuối cùng 100% đạt chuẩn Zero-Hallucination.
    """
    valid_bullet = GeneratedBullet(
        text="Engineered REST APIs on Cloudflare Workers and Hono sustaining 200 req/min rate limit capacity.",
        evidence_ids=["project.account_manager__zero_knowledge_password_vault.bullet_2"],
        claims=[]
    )

    invalid_bullet = GeneratedBullet(
        text="Managed Kubernetes clusters and Kafka brokers achieving 99.999% uptime.",
        evidence_ids=["project.account_manager__zero_knowledge_password_vault.bullet_2"],
        claims=[]
    )

    draft = StructuredResumeDraft(
        target_title="Backend Developer Intern",
        professional_summary=GeneratedSummary(
            text="Final-year student specializing in backend software engineering with Cloudflare Workers.",
            evidence_ids=["education.inst_1", "project.account_manager__zero_knowledge_password_vault.bullet_2"],
            claims=[]
        ),
        priority_skills=["Cloudflare Workers", "Hono", "TypeScript", "REST API"],
        projects=[
            GeneratedProject(
                source_project_name="Account Manager: Zero-Knowledge Password Vault",
                bullets=[valid_bullet, invalid_bullet],
            )
        ]
    )

    # Chạy validation report ban đầu
    initial_report = claim_validator.validate_draft(draft, sample_evidence_bundle)
    assert not initial_report.is_valid
    assert len(initial_report.violations) > 0

    # Chạy Unit Regeneration Orchestrator
    validated_draft, final_report = await unit_regeneration_orchestrator.validate_and_regenerate(
        draft=draft,
        bundle=sample_evidence_bundle,
        max_retries=2,
    )

    # Bullet 1 hợp lệ ban đầu phải được giữ nguyên văn
    assert validated_draft.projects[0].bullets[0].text == valid_bullet.text
    # Bản CV cuối cùng phải 100% Valid
    assert final_report.is_valid is True
    assert final_report.provenance_score == 100.0


# ============================================================================
# TEST 8: Cross-Role Differentiation on Same Candidate Profile
# ============================================================================

def test_cross_role_differentiation(sample_candidate_with_facts):
    """
    Test 8: Cùng 1 hồ sơ ứng viên nhưng:
    - Backend JD -> Chiến lược định vị Backend & API.
    - Security JD -> Chiến lược định vị Cryptography & Zero-Knowledge.
    """
    job_be = Job(
        title="Backend Developer Intern",
        description="REST APIs, Hono, Cloudflare Workers, Database, Rate Limiting",
    )
    job_sec = Job(
        title="Cyber Security Intern",
        description="Cryptography, PKI, Shamir Secret Sharing, Argon2id, Zero-Knowledge",
    )

    bundle_be = resume_intelligence.build_evidence_bundle(sample_candidate_with_facts, job_be)
    bundle_sec = resume_intelligence.build_evidence_bundle(sample_candidate_with_facts, job_sec)

    assert bundle_be.strategy.role_family == "backend"
    assert bundle_sec.strategy.role_family == "security"

    # Positioning phải khác nhau
    assert bundle_be.strategy.positioning != bundle_sec.strategy.positioning
    assert "Backend" in bundle_be.strategy.positioning
    assert "Cryptography" in bundle_sec.strategy.positioning


# ============================================================================
# TEST 9: Deterministic Composer Offline Fallback
# ============================================================================

def test_deterministic_composer_fallback(sample_evidence_bundle):
    """
    Test 9: Deterministic Resume Composer sinh draft hoàn toàn không qua mạng,
    đạt 100% hợp lệ qua ClaimLevelValidator ngay lần đầu tiên.
    """
    composer_draft = deterministic_composer.compose_draft(sample_evidence_bundle)

    assert composer_draft.target_title == sample_evidence_bundle.strategy.target_role
    assert len(composer_draft.projects) > 0
    assert len(composer_draft.professional_summary.text) > 20

    # Phải 100% pass validator
    report = claim_validator.validate_draft(composer_draft, sample_evidence_bundle)
    assert report.is_valid is True
    assert report.provenance_score == 100.0


# ============================================================================
# TEST 10: Architectural Scope Shift (Detected and Rejected)
# ============================================================================

def test_architectural_scope_shift_rejected(sample_evidence_bundle):
    """
    Test 10: Phát hiện trôi dời định ngữ kiến trúc:
    Nếu bằng chứng gốc ghi nhận 'client-side Argon2id password hashing',
    nhưng bullet bị LLM viết lược bỏ 'client-side' (thành 'server-side Argon2id hashing')
    -> Phải bị bắt lỗi ARCHITECTURAL_SCOPE_SHIFT.
    """
    shifted_bullet = GeneratedBullet(
        text="Implemented server-side authentication with Argon2id password hashing (t=3, m=64MB) and token-bucket rate limiting.",
        evidence_ids=["project.account_manager__zero_knowledge_password_vault.bullet_1"],
        claims=[]
    )

    violations = claim_validator.validate_bullet(
        bullet=shifted_bullet,
        unit_id="test.bullet_scope_shift",
        project_name="Account Manager: Zero-Knowledge Password Vault",
        bundle=sample_evidence_bundle,
    )

    assert len(violations) > 0
    violation_types = [v.violation_type for v in violations]
    assert ValidationViolationType.ARCHITECTURAL_SCOPE_SHIFT in violation_types

