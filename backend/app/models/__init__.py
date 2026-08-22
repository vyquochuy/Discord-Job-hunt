"""SQLAlchemy Models package."""
from app.models.candidate import (
    Candidate,
    CandidateSkill,
    CandidateExperience,
    CandidateProject,
    CandidateCertification,
)
from app.models.job import (
    WorkModeEnum,
    JobLevelEnum,
    JobStatusEnum,
    RawJobStatusEnum,
    SkillCategoryEnum,
    RawJob,
    Job,
    Skill,
    SkillAlias,
    JobSkill,
)

from app.models.match import JobMatch

__all__ = [
    # Candidate Models (Phase 1)
    "Candidate",
    "CandidateSkill",
    "CandidateExperience",
    "CandidateProject",
    "CandidateCertification",
    # Job Collection Models (Phase 2)
    "WorkModeEnum",
    "JobLevelEnum",
    "JobStatusEnum",
    "RawJobStatusEnum",
    "SkillCategoryEnum",
    "RawJob",
    "Job",
    "Skill",
    "SkillAlias",
    "JobSkill",
    # Match Models (Phase 3)
    "JobMatch",
]

