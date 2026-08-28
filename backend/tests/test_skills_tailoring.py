import pytest
from app.models.candidate import Candidate, CandidateProject, CandidateSkill
from app.schemas.tailoring_ir import (
    EvidenceBundle,
    GeneratedBullet,
    GeneratedClaimFragment,
    GeneratedProject,
    GeneratedSkillCategory,
    GeneratedSummary,
    LayoutBudget,
    StructuredResumeDraft,
    TailoringStrategy,
    ValidationViolationType,
)
from app.services.tailoring.deterministic_composer import deterministic_composer
from app.services.tailoring.evidence_validator import claim_validator
from app.services.tailoring.fact_graph import fact_graph_builder
from app.services.tailoring.latex_generator import latex_generator


@pytest.fixture
def sample_candidate_with_skills():
    c = Candidate(
        id="cand-001",
        full_name="Vy Quoc Huy",
        headline="Software Engineer Intern",
        email="vyquochuy305@gmail.com",
        phone="(+84) 384988934",
        summary="Backend Software Engineer focusing on distributed systems and cryptography.",
        skills=[
            CandidateSkill(name="Python", category="programming"),
            CandidateSkill(name="FastAPI", category="frameworks"),
            CandidateSkill(name="PostgreSQL", category="tools_databases"),
            CandidateSkill(name="Redis", category="tools_databases"),
            CandidateSkill(name="C++", category="programming"),
            CandidateSkill(name="Argon2id", category="security"),
        ],
        projects=[
            CandidateProject(
                name="Vault Project",
                summary="Zero knowledge password vault with Argon2id and FastAPI.",
                technologies=["Python", "FastAPI", "Argon2id", "PostgreSQL"],
                evidence_points=[
                    {"title": "Core Security", "detail": "Implemented client-side Argon2id hashing with latency ~45ms."}
                ],
            )
        ],
    )
    return c


@pytest.fixture
def sample_bundle(sample_candidate_with_skills):
    evidence_facts = list(fact_graph_builder.build_evidence_registry(sample_candidate_with_skills).values())
    strategy = TailoringStrategy(
        target_role="Backend Developer Intern",
        positioning="High-Throughput Backend APIs & Cryptography",
        role_family="backend",
        prioritized_skills=["FastAPI", "Python", "PostgreSQL", "Redis"],
        deprioritized_skills=[],
        selected_projects=["Vault Project"],
        selected_evidence_ids=["project.vault_project.bullet_1"],
        jd_keywords_to_target=["FastAPI", "PostgreSQL", "Redis"],
        unsupported_requirements=["Kubernetes", "AWS DynamoDB"],
        allowed_technologies=["python", "fastapi", "postgresql", "redis", "c++", "argon2id"],
        allowed_metrics=["~45ms"],
        allowed_claims=["client-side Argon2id hashing"],
    )
    return EvidenceBundle(
        strategy=strategy,
        evidence_facts=evidence_facts,
        target_jd_summary={"title": "Backend Intern", "requirements": "FastAPI, PostgreSQL"},
        layout_budget=LayoutBudget(),
    )


def test_deterministic_composer_generates_tailored_skills(sample_bundle):
    """Xác minh Deterministic Composer tự động sinh cấu trúc tailored_skills có phân loại."""
    draft = deterministic_composer.compose_draft(sample_bundle)
    assert draft is not None
    assert len(draft.tailored_skills) > 0
    
    cat_names = [cat.category_name for cat in draft.tailored_skills]
    assert "Programming Languages" in cat_names
    assert "Frameworks & Libraries" in cat_names


def test_claim_level_validator_validates_tailored_skills_success(sample_bundle):
    """Xác minh Validator duyệt qua bản draft có tailored_skills hợp lệ."""
    valid_bullet = GeneratedBullet(
        text="Implemented client-side Argon2id hashing with latency ~45ms.",
        evidence_ids=["project.vault_project.bullet_1"],
        claims=[GeneratedClaimFragment(claim="client-side Argon2id hashing", evidence_ids=["project.vault_project.bullet_1"])],
    )

    draft = StructuredResumeDraft(
        target_title="Backend Developer Intern",
        professional_summary=GeneratedSummary(
            text="Backend Engineer focusing on FastAPI and PostgreSQL.",
            evidence_ids=["candidate.identity"],
            claims=[GeneratedClaimFragment(claim="Backend Engineer focusing on FastAPI", evidence_ids=["candidate.identity"])],
        ),
        priority_skills=["FastAPI", "Python", "PostgreSQL"],
        tailored_skills=[
            GeneratedSkillCategory(
                category_name="Backend & Distributed APIs",
                skills=["FastAPI", "Python", "PostgreSQL", "Redis"],
            ),
            GeneratedSkillCategory(
                category_name="Security & Cryptography",
                skills=["Argon2id", "C++"],
            ),
        ],
        projects=[
            GeneratedProject(
                source_project_name="Vault Project",
                bullets=[valid_bullet],
            )
        ],
    )

    report = claim_validator.validate_draft(draft, sample_bundle)
    assert report.is_valid
    assert len(report.violations) == 0


def test_claim_level_validator_catches_unsupported_skills_fabrication(sample_bundle):
    """Xác minh Validator phát hiện và bắt lỗi khi Gemini bịa đặt kỹ năng nằm trong UNSUPPORTED_REQUIREMENTS."""
    valid_bullet = GeneratedBullet(
        text="Implemented client-side Argon2id hashing with latency ~45ms.",
        evidence_ids=["project.vault_project.bullet_1"],
        claims=[GeneratedClaimFragment(claim="client-side Argon2id hashing", evidence_ids=["project.vault_project.bullet_1"])],
    )

    # Thêm skill "Kubernetes" (nằm trong unsupported_requirements) và "Rust" (không có trong profile)
    draft_with_hallucinated_skills = StructuredResumeDraft(
        target_title="Backend Developer Intern",
        professional_summary=GeneratedSummary(
            text="Backend Engineer focusing on FastAPI and PostgreSQL.",
            evidence_ids=["candidate.identity"],
            claims=[GeneratedClaimFragment(claim="Backend Engineer focusing on FastAPI", evidence_ids=["candidate.identity"])],
        ),
        priority_skills=["FastAPI", "Python"],
        tailored_skills=[
            GeneratedSkillCategory(
                category_name="Cloud & Container Orchestration",
                skills=["Kubernetes", "AWS DynamoDB", "Rust"],
            )
        ],
        projects=[
            GeneratedProject(
                source_project_name="Vault Project",
                bullets=[valid_bullet],
            )
        ],
    )

    report = claim_validator.validate_draft(draft_with_hallucinated_skills, sample_bundle)
    assert not report.is_valid
    violation_types = [v.violation_type for v in report.violations]
    assert ValidationViolationType.UNSUPPORTED_JD_FABRICATION in violation_types or ValidationViolationType.UNSUPPORTED_TECHNOLOGY in violation_types


def test_latex_generator_renders_tailored_skills(sample_candidate_with_skills):
    """Xác minh LaTeX generator render chính xác các danh mục tailored_skills động."""
    draft = StructuredResumeDraft(
        target_title="Backend Developer Intern",
        professional_summary=GeneratedSummary(
            text="Backend Engineer focusing on FastAPI.",
            evidence_ids=["candidate.identity"],
            claims=[],
        ),
        priority_skills=["FastAPI", "Python"],
        tailored_skills=[
            GeneratedSkillCategory(
                category_name="Core Backend & APIs",
                skills=["FastAPI", "Python", "Hono"],
            ),
            GeneratedSkillCategory(
                category_name="Applied Cryptography & Security",
                skills=["Argon2id", "X.509 PKI"],
            ),
        ],
        projects=[],
    )

    tex = latex_generator.generate_tailored_tex(
        candidate=sample_candidate_with_skills,
        structured_draft=draft,
    )

    assert "Core Backend \\& APIs:" in tex or "Core Backend & APIs:" in tex
    assert "Applied Cryptography \\& Security:" in tex or "Applied Cryptography & Security:" in tex
    assert "FastAPI, Python, Hono" in tex
    assert "Argon2id, X.509 PKI" in tex
