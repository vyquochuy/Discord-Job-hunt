import enum
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.job import JobLevelEnum, WorkModeEnum


# ==============================================================================
# Filter & Eligibility Enums
# ==============================================================================

class FilterStatus(str, enum.Enum):
    PASS = "PASS"        # Requirement chắc chắn được đáp ứng
    FAIL = "FAIL"        # Có bằng chứng rõ ràng candidate vi phạm requirement
    UNKNOWN = "UNKNOWN"  # Thiếu dữ liệu để kết luận (UNKNOWN != PASS, UNKNOWN != FAIL)


class Eligibility(str, enum.Enum):
    ELIGIBLE = "ELIGIBLE"       # Tất cả filter PASS hoặc tối đa 1 UNKNOWN, không có FAIL
    BLOCKED = "BLOCKED"         # Có ít nhất 1 filter FAIL (vi phạm cứng)
    UNCERTAIN = "UNCERTAIN"     # Không có FAIL nhưng có >= 2 filter UNKNOWN


class RecommendationCategory(str, enum.Enum):
    STRONG_MATCH = "STRONG_MATCH"        # Score >= 80 AND ELIGIBLE
    GOOD_MATCH = "GOOD_MATCH"            # Score >= 60 AND ELIGIBLE
    WEAK_MATCH = "WEAK_MATCH"            # Score >= 40 AND ELIGIBLE
    POOR_MATCH = "POOR_MATCH"            # Score < 40 AND ELIGIBLE
    DO_NOT_APPLY = "DO_NOT_APPLY"        # BLOCKED (bất kể điểm số cao bao nhiêu)
    REVIEW_REQUIRED = "REVIEW_REQUIRED"  # UNCERTAIN + Score >= 60


class ConfidenceLevel(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class EvidenceStatus(str, enum.Enum):
    NOT_REQUIRED = "NOT_REQUIRED"                    # Job không yêu cầu tiêu chí này (điểm = 1.0 hoặc N/A)
    SUPPORTED = "SUPPORTED"                          # Tìm thấy bằng chứng rõ ràng trong profile/projects/coursework
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"  # Thiếu bằng chứng để xác minh (điểm trung lập ~0.5)
    MISMATCH = "MISMATCH"                            # Có bằng chứng mâu thuẫn/không đáp ứng (điểm thấp)


class RequirementType(str, enum.Enum):
    TECHNICAL_SKILL = "TECHNICAL_SKILL"      # Ngôn ngữ, framework, database, tool
    DOMAIN_KNOWLEDGE = "DOMAIN_KNOWLEDGE"    # Kiến thức chuyên môn (Web, Mobile, Cryptography, AI/ML)
    COMPETENCY = "COMPETENCY"                # Năng lực cốt lõi (Tư duy logic, Problem Solving, Test-First)
    BEHAVIORAL = "BEHAVIORAL"                # Kỹ năng mềm/hành vi (Giao tiếp, Chủ động, Phản biện)
    EXPERIENCE = "EXPERIENCE"                # Kinh nghiệm làm việc thực tế
    EDUCATION = "EDUCATION"                  # Bằng cấp, chuyên ngành, trạng thái sinh viên
    SENIORITY = "SENIORITY"                  # Cấp bậc (Intern, Fresher, Junior...)
    WORK_CONSTRAINT = "WORK_CONSTRAINT"      # Địa điểm, thời gian, hình thức làm việc


# ==============================================================================
# Evidence & Requirement DTOs
# ==============================================================================

class EvidenceItem(BaseModel):
    source_type: str = Field(..., description="PROJECT | SKILL | EDUCATION | EXPERIENCE | PROFILE | PREFERENCE")
    source_id: Optional[str] = Field(None, description="Tên hoặc ID của nguồn (ví dụ: tên Project)")
    title: str = Field(..., description="Tiêu đề hoặc khía cạnh bằng chứng")
    excerpt: str = Field(..., description="Trích dẫn nội dung hoặc số liệu chứng minh")


class JobRequirementDTO(BaseModel):
    name: str = Field(..., description="Tên yêu cầu (ví dụ: Logical Thinking, Web Development, Python)")
    type: RequirementType = Field(default=RequirementType.COMPETENCY)
    importance: str = Field(default="REQUIRED", description="REQUIRED | PREFERRED")
    normalized_name: Optional[str] = None
    raw_text: Optional[str] = None


class RequirementEvaluation(BaseModel):
    requirement: JobRequirementDTO
    status: EvidenceStatus
    score: float = Field(..., ge=0.0, le=1.0)
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH
    reason: str
    evidences: List[EvidenceItem] = Field(default_factory=list)


# ==============================================================================
# Filter & Signal DTOs
# ==============================================================================

class HardFilterResult(BaseModel):
    filter: str = Field(..., description="Tên bộ lọc: work_mode, location, seniority, salary")
    status: FilterStatus = Field(..., description="Trạng thái: PASS, FAIL, UNKNOWN")
    reason: str = Field(..., description="Lý do chi tiết giải thích kết quả lọc")


class MatchSignal(BaseModel):
    name: str = Field(..., description="Tên tín hiệu: requirement_fit, technical_skill_match, ...")
    score: float = Field(..., ge=0.0, le=1.0, description="Điểm thành phần từ 0.0 đến 1.0")
    weight: float = Field(..., ge=0.0, le=1.0, description="Trọng số tín hiệu")
    confidence: ConfidenceLevel = Field(default=ConfidenceLevel.HIGH, description="Độ tin cậy của dữ liệu")
    evidence_status: EvidenceStatus = Field(default=EvidenceStatus.SUPPORTED, description="Trạng thái bằng chứng")
    reason: str = Field(..., description="Giải thích lý do tính điểm của tín hiệu")
    evidence: List[EvidenceItem] = Field(default_factory=list, description="Danh sách bằng chứng chứng minh")


class SkillMatchResult(BaseModel):
    matched_required: List[str] = Field(default_factory=list)
    missing_required: List[str] = Field(default_factory=list)
    matched_preferred: List[str] = Field(default_factory=list)
    missing_preferred: List[str] = Field(default_factory=list)
    required_coverage: float = Field(default=1.0, ge=0.0, le=1.0)
    preferred_coverage: float = Field(default=1.0, ge=0.0, le=1.0)
    has_technical_requirements: bool = Field(default=True, description="False nếu JD không yêu cầu technical skills cụ thể")


# ==============================================================================
# Candidate & Job DTOs
# ==============================================================================

class CandidateProjectDTO(BaseModel):
    name: str
    role: Optional[str] = None
    summary: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)
    evidence: List[dict[str, Any]] = Field(default_factory=list)


class CandidateExperienceDTO(BaseModel):
    company: str
    role: str
    description: Optional[str] = None
    achievements: List[str] = Field(default_factory=list)


class CandidateEducationDTO(BaseModel):
    institution: str
    degree: Optional[str] = None
    field: Optional[str] = None
    graduation_year: Optional[int] = None
    gpa: Optional[str] = None
    coursework: List[str] = Field(default_factory=list)


class CandidateProfileDTO(BaseModel):
    id: Optional[uuid.UUID] = None
    full_name: str = "Candidate"
    headline: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None
    target_roles: List[str] = Field(default_factory=list)
    target_locations: List[str] = Field(default_factory=list)
    preferences: dict[str, Any] = Field(default_factory=dict)
    skills: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)
    projects: List[CandidateProjectDTO] = Field(default_factory=list)
    experiences: List[CandidateExperienceDTO] = Field(default_factory=list)
    education: List[CandidateEducationDTO] = Field(default_factory=list)

    @property
    def all_skills(self) -> List[str]:
        """Tập hợp kỹ năng bao gồm profile skills và technologies từ projects."""
        skills_set = set(self.skills)
        for proj in self.projects:
            for tech in proj.technologies:
                if tech and tech.strip():
                    skills_set.add(tech.strip())
        return list(skills_set)

    @property
    def all_coursework(self) -> List[str]:
        """Tổng hợp danh sách các môn học chính."""
        cw: List[str] = []
        for edu in self.education:
            cw.extend(edu.coursework)
        return list(set(cw))


class JobMatchInputDTO(BaseModel):
    id: Optional[uuid.UUID] = None
    title: str
    company_name: str
    location: Optional[str] = None
    normalized_location: Optional[str] = None
    work_mode: WorkModeEnum = WorkModeEnum.ONSITE
    level: JobLevelEnum = JobLevelEnum.UNKNOWN
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    salary_currency: Optional[str] = None
    is_salary_negotiable: bool = False
    description: str = ""
    requirements_summary: Optional[str] = None
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    schedule: Optional[str] = None
    experience_required: Optional[str] = None
    education_required: Optional[str] = None
    requirements: List[JobRequirementDTO] = Field(default_factory=list)
    embedding: Optional[List[float]] = None

    @property
    def all_skills(self) -> List[str]:
        return list(set(self.required_skills + self.preferred_skills))


# ==============================================================================
# Snapshots & Final Result
# ==============================================================================

class CandidateSnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore")

    skills: List[str] = Field(default_factory=list)
    target_roles: List[str] = Field(default_factory=list)
    target_locations: List[str] = Field(default_factory=list)
    location: Optional[str] = None
    work_mode_preference: Optional[str] = None
    minimum_salary: Optional[float] = None
    salary_currency: Optional[str] = None
    education_count: int = 0
    experience_count: int = 0
    project_count: int = 0
    captured_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class JobSnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str
    company: str
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    work_mode: str
    level: str
    location: Optional[str] = None
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    salary_currency: Optional[str] = None
    is_salary_negotiable: bool = False
    captured_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MatchScoreResult(BaseModel):
    score: float = Field(..., ge=0.0, le=100.0, description="Điểm chất lượng phù hợp 0 - 100")
    eligibility: Eligibility = Field(..., description="Trạng thái tư cách ứng tuyển")
    eligibility_reasons: List[str] = Field(default_factory=list, description="Lý do chi tiết nếu bị BLOCKED hoặc UNCERTAIN")
    recommendation: RecommendationCategory = Field(..., description="Phân loại khuyến nghị ứng tuyển")
    signals: List[MatchSignal] = Field(default_factory=list, description="Chi tiết 7 tín hiệu thành phần")
    hard_filter_results: List[HardFilterResult] = Field(default_factory=list, description="Chi tiết 4 hard filters")
    skill_match: SkillMatchResult = Field(default_factory=SkillMatchResult, description="Chi tiết so khớp kỹ năng")
    requirement_evaluations: List[RequirementEvaluation] = Field(default_factory=list, description="Chi tiết đánh giá bằng chứng theo từng yêu cầu")
    scoring_version: str = "v2"
    taxonomy_version: str = "v1"
    warnings: List[str] = Field(default_factory=list)
