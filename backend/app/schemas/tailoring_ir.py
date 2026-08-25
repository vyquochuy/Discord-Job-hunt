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
    ):
        self.project_name = project_name
        self.evidence_title = evidence_title
        self.evidence_detail = evidence_detail
        self.technologies = technologies or []

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
