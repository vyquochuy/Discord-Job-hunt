import pytest
from app.models.candidate import Candidate, CandidateProject
from app.models.job import Job, JobLevelEnum, WorkModeEnum
from app.services.tailoring.cover_letter_generator import (
    CoverLetterDraft,
    CoverLetterGenerator,
    CoverLetterLinter,
    FeaturedProjectDraft,
    cover_letter_generator,
)


@pytest.fixture
def sample_candidate():
    return Candidate(
        full_name="Nguyen Van A",
        headline="Software Engineer Intern",
        email="nguyenvana@example.com",
        phone="(+84) 123456789",
        location="Thu Duc, Ho Chi Minh",
        education=[
            {
                "institution": "Hanoi University of Science and Technology",
                "field": "Computer Science",
                "degree": "Bachelor",
                "graduation_year": 2026,
            }
        ],
        projects=[
            CandidateProject(
                name="AI Job Hunter System",
                role="Sole Developer",
                summary="Asynchronous microservices backend with FastAPI, PostgreSQL, and Redis",
                technologies=["Python", "FastAPI", "PostgreSQL", "Redis", "Docker"],
                evidence_points=[{"title": "Pipeline", "detail": "Engineered 7-signal matching engine"}],
            ),
            CandidateProject(
                name="VYVYCHAT",
                role="Full-stack Developer",
                summary="Real-time messaging platform with Cloudflare Workers",
                technologies=["React", "TypeScript", "Cloudflare Workers", "SQLite"],
                evidence_points=[{"title": "Latency", "detail": "Achieved ~45ms round-trip latency"}],
            ),
            CandidateProject(
                name="Unrelated Mobile Game Demo",
                role="Developer",
                summary="Unity 2D puzzle game",
                technologies=["C#", "Unity"],
            ),
        ],
    )


@pytest.fixture
def sample_job():
    return Job(
        title="Backend Engineer Intern",
        company_name="CloudOps Tech Vietnam",
        location="Ho Chi Minh City",
        work_mode=WorkModeEnum.HYBRID,
        level=JobLevelEnum.INTERN,
        description="Looking for Backend Engineer Intern with experience in Python, FastAPI, PostgreSQL and Redis.",
    )


def test_linter_catches_placeholders(sample_candidate):
    """Kiểm tra linter phát hiện và báo lỗi khi có placeholder như [Company Name] hoặc XYZ Corp."""
    draft_with_placeholder = CoverLetterDraft(
        recipient_company="[Company Name]",
        target_role="Software Intern",
        salutation="Dear [Company Name] Team,",
        hook="I am applying to [Insert Company] for the position.",
        technical_highlights=["Python and FastAPI backend skills"],
        featured_projects=[
            FeaturedProjectDraft(
                project_name="AI Job Hunter System",
                architecture_summary="FastAPI microservice",
                impact_or_metric="Engineered scalable system",
            )
        ],
        company_alignment="I want to work at XYZ Corp.",
        call_to_action="Thank you for considering my application.",
    )

    report = CoverLetterLinter.validate(draft_with_placeholder, sample_candidate)
    assert report.is_valid is False
    assert len(report.placeholder_violations) > 0


def test_linter_detects_cliches(sample_candidate):
    """Kiểm tra linter phát hiện các từ sáo rỗng AI (thrilled to apply, delve, testament...)."""
    draft_with_cliche = CoverLetterDraft(
        recipient_company="CloudOps Tech",
        target_role="Backend Intern",
        salutation="Dear CloudOps Tech Team,",
        hook="I am thrilled to apply for this role and delve into your systems.",
        technical_highlights=["A testament to my backend skills"],
        featured_projects=[
            FeaturedProjectDraft(
                project_name="AI Job Hunter System",
                architecture_summary="FastAPI microservice",
                impact_or_metric="Engineered scalable system",
            )
        ],
        company_alignment="I will seamlessly integrate into your team.",
        call_to_action="Thank you for considering my application.",
    )

    report = CoverLetterLinter.validate(draft_with_cliche, sample_candidate)
    assert len(report.cliche_violations) >= 2


def test_cliche_and_placeholder_autofix():
    """Kiểm tra các hàm tự động sửa lỗi cliché và placeholder."""
    dirty_text = "I am thrilled to apply for [Company Name] and delve into your backend architecture."
    clean_text = CoverLetterLinter.replace_cliches(
        CoverLetterLinter.clean_text_from_placeholders(dirty_text, fallback_company="CloudOps Tech")
    )
    assert "[Company Name]" not in clean_text
    assert "thrilled to apply" not in clean_text
    assert "CloudOps Tech" in clean_text


def test_project_pruning_limits_to_top_two(sample_candidate, sample_job):
    """Kiểm tra tầng 2: Project Pruning chỉ chọn tối đa 2 dự án có liên quan nhất."""
    parsed_jd = CoverLetterGenerator._extract_jd_schema(sample_job)
    featured = CoverLetterGenerator._prune_and_rank_projects(sample_candidate, parsed_jd)

    assert len(featured) <= 2
    project_names = [f.project_name for f in featured]
    # Phải ưu tiên AI Job Hunter System vì khớp Python/Postgres
    assert "AI Job Hunter System" in project_names
    assert "Unrelated Mobile Game Demo" not in project_names


def test_end_to_end_cover_letter_generation(sample_candidate, sample_job):
    """Kiểm tra toàn bộ pipeline sinh Cover Letter và đạt 100% Guardrails."""
    result = cover_letter_generator.generate_cover_letter(
        candidate=sample_candidate,
        job=sample_job,
    )

    assert result["company_name"] == "CloudOps Tech Vietnam"
    assert "validation_report" in result
    assert result["validation_report"]["is_valid"] is True
    assert len(result["validation_report"]["placeholder_violations"]) == 0

    markdown = result["content_markdown"]
    assert "# Cover Letter" in markdown
    assert "CloudOps Tech Vietnam" in markdown
    assert "Nguyen Van A" in markdown
    assert "AI Job Hunter System" in markdown
    assert "[Insert" not in markdown
    assert "[Company" not in markdown
