import logging
import uuid
import pytest
from app.models.job import (
    Job,
    JobLevelEnum,
    JobSkill,
    JobStatusEnum,
    RawJob,
    RawJobStatusEnum,
    Skill,
    SkillAlias,
    SkillCategoryEnum,
    WorkModeEnum,
)
from app.schemas.job import (
    JobCreate,
    JobDetailResponse,
    JobExtractedData,
    JobResponse,
    RawJobCreate,
    SkillTaxonomyCreate,
)

logger = logging.getLogger("test.job_models")


def test_raw_job_and_standardized_job_schema():
    """Kiểm tra Pydantic schemas cho RawJob và Job."""
    logger.info("=== [TEST] RawJob & Job Pydantic Schema Validation ===")
    
    raw_create = RawJobCreate(
        source="itviec",
        source_url="https://itviec.com/it-jobs/senior-python-developer",
        source_job_id="12345",
        content_hash="a"*64,
        raw_payload={"title": "Senior Python Developer", "company": "FPT Software"},
        raw_html="<div>Test JD</div>",
        fetch_status=RawJobStatusEnum.FETCHED,
    )
    logger.info(f"  RawJobCreate Schema Validated: Source={raw_create.source}, Hash={raw_create.content_hash[:12]}...")
    assert raw_create.source == "itviec"
    assert len(raw_create.content_hash) == 64

    job_create = JobCreate(
        raw_job_id=uuid.uuid4(),
        title="Senior Python Developer",
        normalized_title="Senior Python Developer",
        company_name="FPT Software Co., Ltd",
        normalized_company="FPT Software",
        location="Ho Chi Minh City",
        normalized_location="Ho Chi Minh City",
        work_mode=WorkModeEnum.HYBRID,
        level=JobLevelEnum.SENIOR,
        min_salary=2000.0,
        max_salary=3500.0,
        salary_currency="USD",
        description="Experience in Python, FastAPI, Docker",
        status=JobStatusEnum.ACTIVE,
    )
    logger.info(f"  JobCreate Schema Validated: Normalized Company='{job_create.normalized_company}', Level={job_create.level.value}")
    assert job_create.normalized_company == "FPT Software"
    assert job_create.level == JobLevelEnum.SENIOR


def test_job_orm_models_instantiation():
    """Kiểm tra quan hệ ORM giữa RawJob, Job, Skill, SkillAlias và JobSkill."""
    logger.info("=== [TEST] Job ORM Models Instantiation & Relationships ===")
    
    raw_id = uuid.uuid4()
    raw_job = RawJob(
        id=raw_id,
        source="remotive",
        source_url="https://remotive.com/job/100",
        source_job_id="100",
        content_hash="b"*64,
        fetch_status=RawJobStatusEnum.FETCHED.value,
    )

    job = Job(
        id=uuid.uuid4(),
        raw_job_id=raw_id,
        title="DevOps Engineer",
        normalized_title="DevOps Engineer",
        company_name="Cloud Corp",
        normalized_company="Cloud Corp",
        work_mode=WorkModeEnum.REMOTE,
        level=JobLevelEnum.MID,
        description="Kubernetes, AWS, Terraform",
        status=JobStatusEnum.ACTIVE,
    )
    raw_job.job = job

    skill = Skill(
        id=uuid.uuid4(),
        canonical_name="Kubernetes",
        category=SkillCategoryEnum.TOOL,
    )
    alias = SkillAlias(
        id=uuid.uuid4(),
        skill_id=skill.id,
        alias="k8s",
    )
    skill.aliases.append(alias)

    job_skill = JobSkill(
        id=uuid.uuid4(),
        job_id=job.id,
        skill_id=skill.id,
        is_required=True,
        confidence=1.0,
        source="explicit",
    )
    job.skills.append(job_skill)

    logger.info(f"  RawJob 1-1 Job Relationship: RawJob.job.title = '{raw_job.job.title}'")
    logger.info(f"  Skill 1-N Aliases: Skill '{skill.canonical_name}' -> Alias '{skill.aliases[0].alias}'")
    logger.info(f"  Job N-N Skills (via JobSkill): is_required={job.skills[0].is_required}, confidence={job.skills[0].confidence}")

    assert raw_job.job.title == "DevOps Engineer"
    assert len(skill.aliases) == 1
    assert skill.aliases[0].alias == "k8s"
    assert len(job.skills) == 1
    assert job.skills[0].is_required is True
