import uuid
import pytest
from app.models.candidate import (
    Candidate,
    CandidateSkill,
    CandidateExperience,
    CandidateProject,
    CandidateCertification,
)
from app.schemas.candidate import (
    CandidateCreate,
    CandidateDetailResponse,
    SkillCreate,
    ExperienceCreate,
    ProjectCreate,
    CertificationCreate,
)


def test_candidate_pydantic_schemas_validation():
    """Kiểm tra Pydantic schemas validate chính xác dữ liệu từ hồ sơ ứng viên."""
    candidate_data = {
        "full_name": "Vy Quoc Huy",
        "headline": "System Intern",
        "email": "vyquochuy305@gmail.com",
        "phone": "(+84) 384988934",
        "location": "Thu Duc, Ho Chi Minh",
        "github_url": "https://github.com/vyquochuy",
        "linkedin_url": "https://www.linkedin.com/in/vyquochuy/",
        "summary": "Final-year Computer Science student interested in Linux systems & cloud infrastructure.",
        "education": [
            {
                "institution": "VNUHCM - University of Science",
                "degree": "Bachelor",
                "field": "Computer Science - Cyber Security",
                "graduation_year": 2026,
                "gpa": "3.15/4.0",
                "coursework": [
                    "Computer Networks",
                    "Database Systems",
                    "Cryptography",
                ],
            }
        ],
        "target_roles": ["System Intern", "DevOps Engineer", "Backend Developer"],
        "target_locations": ["Ho Chi Minh City", "Remote"],
        "preferences": {
            "employment_types": ["Internship", "Full-time"],
            "remote": "hybrid",
            "minimum_salary": None,
            "currency": "VND",
        },
    }

    # Validate qua CandidateCreate schema
    schema = CandidateCreate(**candidate_data)
    assert schema.full_name == "Vy Quoc Huy"
    assert schema.headline == "System Intern"
    assert len(schema.education) == 1
    assert schema.education[0]["gpa"] == "3.15/4.0"
    assert len(schema.target_roles) == 3


def test_project_schema_with_evidence():
    """Kiểm tra schema Project chứa các evidence points đo lường định lượng."""
    project_data = {
        "name": "VYVYCHAT",
        "role": "Full-stack Developer",
        "summary": "Real-time messaging platform on Cloudflare serverless",
        "period": "May 2026 -- Jun 2026",
        "repository_url": "https://github.com/vyquochuy/vyvychat",
        "demo_url": "https://vyvychat.myvault-service.workers.dev/",
        "technologies": [
            "React",
            "TypeScript",
            "Tailwind CSS",
            "Cloudflare Workers",
            "Durable Objects",
        ],
        "evidence_points": [
            {
                "title": "Cryptography & E2EE",
                "detail": "Architected zero-knowledge E2EE with ECDH P-256 key exchange.",
            },
            {
                "title": "Stateful Real-Time Edge",
                "detail": "Measured round-trip latency of ~45ms under concurrent load.",
            },
        ],
        "order": 1,
    }

    schema = ProjectCreate(**project_data)
    assert schema.name == "VYVYCHAT"
    assert len(schema.evidence_points) == 2
    assert schema.evidence_points[0]["title"] == "Cryptography & E2EE"


def test_candidate_orm_model_instantiation():
    """Kiểm tra khởi tạo SQLAlchemy ORM model với quan hệ cascade."""
    candidate_id = uuid.uuid4()
    candidate = Candidate(
        id=candidate_id,
        full_name="Vy Quoc Huy",
        headline="System Intern",
        email="vyquochuy305@gmail.com",
    )

    skill = CandidateSkill(
        id=uuid.uuid4(),
        candidate_id=candidate_id,
        category="programming",
        name="Python",
        proficiency="Advanced",
    )

    project = CandidateProject(
        id=uuid.uuid4(),
        candidate_id=candidate_id,
        name="Account Manager",
        role="Author",
        technologies=["Flutter", "Dart", "Hono", "Cloudflare Workers"],
    )

    candidate.skills.append(skill)
    candidate.projects.append(project)

    assert candidate.full_name == "Vy Quoc Huy"
    assert len(candidate.skills) == 1
    assert candidate.skills[0].name == "Python"
    assert len(candidate.projects) == 1
    assert candidate.projects[0].name == "Account Manager"
