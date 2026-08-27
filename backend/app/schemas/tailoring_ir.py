import enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class SkillRequirementType(str, enum.Enum):
    """Phân loại mức độ ưu tiên của kỹ năng theo yêu cầu JD."""
    REQUIRED = "REQUIRED"          # Bắt buộc (Must-have trong JD)
    PREFERRED = "PREFERRED"        # Ưu tiên / Điểm cộng (Nice-to-have / Plus)
    IMPLICIT = "IMPLICIT"          # Kỹ năng nền tảng ngầm hiểu (vd: Backend cần Git, SQL, Linux)
    IRRELEVANT = "IRRELEVANT"      # Không liên quan trực tiếp đến bài toán


class ClaimVerificationStatus(str, enum.Enum):
    """Trạng thái kiểm chứng của một atomic claim đối với Fact Graph."""
    VERIFIED = "VERIFIED"                      # Khớp chính xác fact có cấu trúc và metric
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"  # Khớp hành động và công nghệ, nhưng metric không có sẵn
    UNVERIFIED = "UNVERIFIED"                  # Hoàn toàn không tìm thấy căn cứ trong Fact Graph
    CONFLICTING = "CONFLICTING"                # Mâu thuẫn trực tiếp với hồ sơ thực tế


@dataclass(frozen=True)
class MetricFact:
    """Thông số kỹ thuật hoặc chỉ số định lượng được chứng thực."""
    metric_id: str
    numeric_value: float
    unit: str                         # ms, s, %, req/min, MB, GB, devices, tables, ...
    context: str                      # "round-trip latency", "rate limit capacity", ...
    raw_token: str                    # "~45ms", "200 req/min", "3-of-5 threshold"
    is_exact: bool = True


@dataclass
class FactNode:
    """Nút sự thật bất biến trong Đồ thị Bằng chứng (Fact Graph)."""
    fact_id: str                      # "project.account_manager.rate_limiting"
    entity_type: str                  # "PROJECT", "EXPERIENCE", "EDUCATION", "SKILL", "CANDIDATE"
    entity_id: str                    # "Account Manager", "VNUHCM-US", "Vy Quoc Huy"
    raw_statement: str                # Nội dung nguyên bản không biến đổi
    technologies: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    metrics: List[MetricFact] = field(default_factory=list)
    is_core: bool = False             # Đánh dấu Core Evidence bất biến của dự án


@dataclass
class CoreEvidence:
    """Primary Technical Differentiator / USP của dự án (Bắt buộc, duy nhất 1)."""
    title: str
    description: str
    technology_refs: List[str] = field(default_factory=list)
    is_core: bool = True


@dataclass
class SupportingEvidence:
    """Minh chứng kỹ thuật bổ trợ (Tùy chọn, xếp hạng và chọn lọc linh hoạt theo JD)."""
    title: str
    detail: str
    technologies: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    metrics: List[str] = field(default_factory=list)
    is_core: bool = False


@dataclass
class ProjectEvidenceModel:
    """Mô hình minh chứng dự án 3 lớp chuẩn hóa + lớp mở rộng."""
    name: str
    summary: str                                        # 1 câu ngắn factual tổng quan
    core: CoreEvidence                                  # 1 Core evidence bắt buộc
    technologies: List[str]                             # Ground truth tech stack duy nhất
    supporting_evidence: List[SupportingEvidence] = field(default_factory=list)
    role: Optional[str] = None
    period: Optional[str] = None
    repository_url: Optional[str] = None
    demo_url: Optional[str] = None


@dataclass
class JDCapabilityProfile:
    """Phổ năng lực đa chiều và phân loại yêu cầu của một Job Description."""
    capability_vector: Dict[str, float]       # {"backend": 0.85, "database": 0.70, "security": 0.40, ...}
    primary_domains: List[str]                # ["backend", "cloud_infrastructure"]
    skill_classifications: Dict[str, SkillRequirementType] = field(default_factory=dict)
    core_problem_statements: List[str] = field(default_factory=list)
    seniority_level: str = "INTERN"           # "INTERN", "FRESHER", "JUNIOR", "MID", "SENIOR"
    normalized_role_title: str = "Software Engineer"
    confidence: float = 1.0


@dataclass
class ScoredEvidenceItem:
    """Minh chứng kỹ thuật đã được lượng hóa điểm số liên quan đối với JD."""
    project_name: str
    evidence_title: str
    evidence_detail: str
    technologies: List[str] = field(default_factory=list)
    total_score: float = 1.0                  # 0.0 - 1.0 (Composite Score)
    responsibility_score: float = 0.5         # Match với problem statements của JD
    capability_score: float = 0.5             # Khớp vector năng lực
    tech_fit_score: float = 0.5               # Khớp công nghệ theo phân cấp Required/Preferred
    evidence_strength_score: float = 0.5      # Trọng số định lượng & tech count
    jd_importance_weight: float = 1.0         # Hệ số ưu tiên của JD
    irrelevance_penalty: float = 0.0          # Mức phạt công nghệ lệch pha
    matched_capabilities: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    metrics: List[str] = field(default_factory=list)
    fact_node: Optional[FactNode] = None
    is_core: bool = False                     # Cờ đánh dấu minh chứng là Core USP bất biến

    def __init__(
        self,
        project_name: str,
        evidence_title: str,
        evidence_detail: str,
        technologies: Optional[List[str]] = None,
        score: Any = None,
        capabilities: Any = None,
        total_score: Optional[float] = None,
        responsibility_score: float = 0.5,
        capability_score: float = 0.5,
        tech_fit_score: float = 0.5,
        evidence_strength_score: float = 0.5,
        jd_importance_weight: float = 1.0,
        irrelevance_penalty: float = 0.0,
        matched_capabilities: Optional[List[str]] = None,
        metrics: Optional[List[str]] = None,
        fact_node: Optional[FactNode] = None,
        is_core: bool = False,
    ):
        self.project_name = project_name
        self.evidence_title = evidence_title
        self.evidence_detail = evidence_detail
        self.technologies = technologies or []
        self.is_core = is_core or (fact_node.is_core if fact_node else False)

        # Xử lý linh hoạt cả positional và keyword arguments
        final_sc = 1.0
        if total_score is not None:
            final_sc = float(total_score)
        elif isinstance(score, (int, float)):
            final_sc = float(score)
        elif isinstance(capabilities, (int, float)):
            final_sc = float(capabilities)

        caps = []
        if isinstance(capabilities, list):
            caps = capabilities
        elif isinstance(score, list):
            caps = score
        elif matched_capabilities:
            caps = matched_capabilities

        self.total_score = final_sc
        self.responsibility_score = responsibility_score
        self.capability_score = capability_score
        self.tech_fit_score = tech_fit_score
        self.evidence_strength_score = evidence_strength_score
        self.jd_importance_weight = jd_importance_weight
        self.irrelevance_penalty = irrelevance_penalty
        self.matched_capabilities = caps
        self.capabilities = caps
        self.metrics = metrics or []
        self.fact_node = fact_node

    @property
    def is_protected(self) -> bool:
        """Core evidence luôn được bảo vệ khỏi bị drop."""
        return self.is_core

    @property
    def score(self) -> float:
        return self.total_score

    @score.setter
    def score(self, val: float):
        self.total_score = val


@dataclass
class DecomposedClaim:
    """Một mệnh đề nguyên tử được phân rã từ bullet point để kiểm chứng độc lập."""
    claim_id: str
    bullet_ref: str
    action_text: str
    technologies: List[str] = field(default_factory=list)
    claimed_metrics: List[str] = field(default_factory=list)
    expected_fact_id: Optional[str] = None
    status: ClaimVerificationStatus = ClaimVerificationStatus.UNVERIFIED
    matched_fact_id: Optional[str] = None
    audit_notes: str = ""


@dataclass
class LayoutBudget:
    """Ngân sách bố cục vật lý để đảm bảo Resume vừa vặn chuẩn 1 trang A4 ATS."""
    min_projects: int = 2
    max_projects: int = 3
    max_total_bullets: int = 7
    max_bullets_per_project: int = 3
    min_bullets_per_project: int = 1
    min_project_threshold: float = 0.35
    min_bullet_threshold: float = 0.30
    max_summary_lines: int = 4
    max_skills_lines: int = 6


@dataclass
class ScoredProjectCandidate:
    """Dự án ứng viên kèm điểm số và tập minh chứng đã xếp hạng."""
    project: Any                              # CandidateProject model or dict
    project_score: float
    ranked_evidence: List[ScoredEvidenceItem]
    capabilities: List[str] = field(default_factory=list)
    matched_technologies: List[str] = field(default_factory=list)
    diversity_bonus: float = 0.0
    redundancy_penalty: float = 0.0
    final_score: float = 0.0
    selection_reason: str = ""


@dataclass
class ProjectScoringDetail:
    """Chi tiết điểm số đa tín hiệu của một dự án."""
    project_name: str
    relevance_score: float
    role_fit_score: float
    tech_overlap_score: float
    irrelevance_penalty: float
    final_score: float
    capabilities: List[str] = field(default_factory=list)
    selection_reasons: List[str] = field(default_factory=list)


@dataclass
class ProjectSelectionResult:
    """Kết quả chọn dự án và giải trình."""
    selected_projects: List[ScoredProjectCandidate]
    rejected_projects: List[ScoredProjectCandidate]
    scores: Dict[str, float] = field(default_factory=dict)
    reasons: Dict[str, str] = field(default_factory=dict)
    scoring_details: Dict[str, ProjectScoringDetail] = field(default_factory=dict)
    layout_budget: Optional[LayoutBudget] = None


@dataclass
class ResumeStrategy:
    """
    Intermediate Representation (IR / Single Source of Truth) cho Resume & Cover Letter.
    """
    role_family: str                          # Backward compatibility ("backend", "system", "security", "general")
    target_title: str
    adaptive_summary: str
    priority_skills: List[str]                # Sắp xếp theo JD Importance x Evidence
    ranked_projects: List[ScoredProjectCandidate]
    selected_projects: List[ScoredProjectCandidate]
    selected_evidence: List[ScoredEvidenceItem]
    matched_skills: List[str]
    top_capabilities: List[str] = field(default_factory=list)
    jd_capability_profile: Optional[JDCapabilityProfile] = None
    layout_budget: Optional[LayoutBudget] = None
    project_selection_result: Optional[Any] = None
    explainability_matrix: Dict[str, Any] = field(default_factory=dict)
    all_projects: List[ScoredProjectCandidate] = field(default_factory=list)
    all_scored_evidence: List[ScoredEvidenceItem] = field(default_factory=list)


# ============================================================================
# Architectural Refactor: Enhanced Evidence, Generation & Validation Models
# ============================================================================

class EvidenceCategory(str, enum.Enum):
    """Phân loại danh mục của một bằng chứng / sự thật từ hồ sơ ứng viên."""
    SKILL = "skill"
    PROJECT = "project"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    ACHIEVEMENT = "achievement"


@dataclass
class EvidenceFact:
    """
    Đơn vị bằng chứng nguyên tử (Canonical Traceable Fact) trong Evidence Registry:
    Mọi factual claim có thể tiếp cận bởi Gemini đều phải truy vết về một EvidenceFact.
    """
    id: str                                  # e.g., "project.vivychat.stateful_edge"
    category: EvidenceCategory               # EvidenceCategory enum
    subject: str                             # e.g., "VYVYCHAT", "VNUHCM-US", "Account Manager"
    claim: str                               # Canonical factual claim text
    technologies: List[str] = field(default_factory=list)
    metrics: List[str] = field(default_factory=list)       # Raw tokens, e.g. ["~45ms", "200 req/min"]
    source: str = ""                         # e.g., "candidate.projects.vyvychat.bullet_1"
    confidence: str = "explicit"             # "explicit" | "verified"
    is_core: bool = False                    # Core USP bất biến của dự án
    capabilities: List[str] = field(default_factory=list)
    canonical_technologies: List[str] = field(default_factory=list)  # Normalized alias IDs


@dataclass
class TailoringStrategy:
    """
    Chiến lược may đo CV định hình định vị và ranh giới nội dung cho Gemini:
    - Quyết định dự án, kỹ năng, định vị chuyên môn.
    - Xác định rõ ràng các khoảng trống (unsupported_requirements) để cấm Gemini bịa đặt.
    """
    target_role: str                         # e.g., "Backend Developer Intern"
    positioning: str                         # e.g., "High-Throughput Serverless & Distributed APIs"
    role_family: str                         # "backend" | "system" | "security" | "general"
    prioritized_skills: List[str]
    deprioritized_skills: List[str]
    selected_projects: List[str]             # Project names
    selected_evidence_ids: List[str]         # Evidence IDs permitted for generation
    jd_keywords_to_target: List[str]
    unsupported_requirements: List[str]      # Gaps in candidate profile relative to JD
    allowed_technologies: List[str]          # All tech tokens supported by selected evidence
    allowed_metrics: List[str]               # All metric tokens supported by selected evidence
    allowed_claims: List[str] = field(default_factory=list)     # Factual claim strings
    forbidden_claims: List[str] = field(default_factory=list)   # Unsupported claims / buzzwords candidate lacks
    explainability_matrix: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvidenceBundle:
    """
    Tập hợp thông tin có cấu trúc được chuyển cho Gemini:
    Chỉ chứa bằng chứng liên quan đã qua chọn lọc, Evidence IDs, JD requirements và constraints.
    """
    strategy: TailoringStrategy
    evidence_facts: List[EvidenceFact]
    target_jd_summary: Dict[str, Any]
    layout_budget: LayoutBudget


# ----------------------------------------------------------------------------
# Pydantic Schemas for Structured Gemini Output with Granular Claims
# ----------------------------------------------------------------------------
from pydantic import BaseModel, Field


class GeneratedClaimFragment(BaseModel):
    """Mảnh mệnh đề hạt nhân (Atomic Claim Fragment) gắn liền với Evidence ID cụ thể."""
    claim: str = Field(..., description="Atomic claim phrase or technology component")
    evidence_ids: List[str] = Field(default_factory=list, description="Evidence IDs supporting this specific fragment")


class GeneratedBullet(BaseModel):
    """Một bullet point được may đo hoàn chỉnh kèm danh sách claim fragments phân rã."""
    text: str = Field(..., description="Full synthesized bullet text tailored for the JD")
    evidence_ids: List[str] = Field(default_factory=list, description="Aggregated Evidence IDs supporting this bullet")
    claims: List[GeneratedClaimFragment] = Field(default_factory=list, description="Granular claim fragments")


class GeneratedProject(BaseModel):
    """Cấu trúc dự án may đo trong Resume."""
    source_project_name: str = Field(..., description="Exact name of the source project")
    bullets: List[GeneratedBullet] = Field(default_factory=list, description="List of generated bullets")


class GeneratedSummary(BaseModel):
    """Tóm tắt mục tiêu / định vị nghề nghiệp may đo."""
    text: str = Field(..., description="Adaptive professional summary statement")
    evidence_ids: List[str] = Field(default_factory=list, description="Evidence IDs supporting the summary")
    claims: List[GeneratedClaimFragment] = Field(default_factory=list, description="Granular claim fragments")


class StructuredResumeDraft(BaseModel):
    """
    Mô hình Resume có cấu trúc sinh bởi Gemini Semantic Writer.
    Phải qua Claim-Level Validator trước khi đưa vào Renderer.
    """
    target_title: str = Field(..., description="Target job title in English")
    professional_summary: GeneratedSummary
    priority_skills: List[str] = Field(default_factory=list)
    projects: List[GeneratedProject] = Field(default_factory=list)


# ----------------------------------------------------------------------------
# Validation Violation and Report Models
# ----------------------------------------------------------------------------

class ValidationViolationType(str, enum.Enum):
    INVALID_EVIDENCE_ID = "INVALID_EVIDENCE_ID"               # Evidence ID không tồn tại trong Evidence Bundle
    UNSUPPORTED_TECHNOLOGY = "UNSUPPORTED_TECHNOLOGY"         # Công nghệ lạ không có trong evidence
    UNSUPPORTED_METRIC = "UNSUPPORTED_METRIC"                 # Số liệu, %, latency, scale bịa đặt
    EXPERIENCE_INFLATION = "EXPERIENCE_INFLATION"             # Nâng cấp sinh viên/bài tập thành production/lead
    UNSUPPORTED_JD_FABRICATION = "UNSUPPORTED_JD_FABRICATION" # Tự chế kinh nghiệm cho yêu cầu JD mà ứng viên không có
    ARCHITECTURAL_SCOPE_SHIFT = "ARCHITECTURAL_SCOPE_SHIFT"   # Trôi dời định ngữ kiến trúc (client-side vs server-side)
    SCHEMA_ERROR = "SCHEMA_ERROR"                             # Lỗi cấu trúc JSON
    SEMANTIC_ALIGNMENT_FAILURE = "SEMANTIC_ALIGNMENT_FAILURE" # Lệch nghĩa so với sự thật gốc


@dataclass
class ValidationViolation:
    violation_type: ValidationViolationType
    section: str                             # "summary" | "project.<name>.bullet_<idx>"
    unit_id: str                             # Unique ID of the bullet or summary
    offending_text: str
    reason: str
    suggested_correction: Optional[str] = None


@dataclass
class ValidationReport:
    is_valid: bool
    provenance_score: float
    violations: List[ValidationViolation] = field(default_factory=list)
    accepted_units_count: int = 0
    total_units_count: int = 0
    locked_units: Dict[str, Any] = field(default_factory=dict)
    feedback_for_regeneration: Optional[str] = None

