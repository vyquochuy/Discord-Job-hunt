"""SQLAlchemy Models package."""
from app.models.user import User
from app.models.saved_job import SavedJob
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

from app.models.resume import (
    ResumeStatusEnum,
    ApplicationStatusEnum,
    ApplicationChannelEnum,
    TailoredResume,
    EvidenceMap,
    CoverLetter,
    ApplicationLog,
)

__all__ = [
    # Auth & Identity Models (Web-First)
    "User",
    "SavedJob",
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
    # Resume & Application Models (Phase 4)
    "ResumeStatusEnum",
    "ApplicationStatusEnum",
    "ApplicationChannelEnum",
    "TailoredResume",
    "EvidenceMap",
    "CoverLetter",
    "ApplicationLog",
]


