import re
from typing import Dict, List, Optional, Tuple

from app.models.job import JobLevelEnum, WorkModeEnum
from app.services.matching.hard_filters import (
    derive_eligibility,
    derive_recommendation,
    evaluate_hard_filters,
    normalize_city_name,
)
from app.services.matching.models import (
    CandidateProfileDTO,
    ConfidenceLevel,
    EvidenceItem,
    EvidenceStatus,
    FilterStatus,
    HardFilterResult,
    JobMatchInputDTO,
    MatchScoreResult,
    MatchSignal,
    SkillMatchResult,
)

from app.services.matching.requirement_matcher import requirement_matcher
from app.services.matching.semantic_matcher import compute_project_relevance
from app.services.matching.skill_matcher import match_skills_deterministic

# ==============================================================================
# 7 Tín hiệu thành phần và trọng số bắt buộc tổng = 1.0 (Invariant Property)
# ==============================================================================
SCORING_WEIGHTS: Dict[str, float] = {
    "requirement_fit": 0.30,        # Năng lực cốt lõi, tư duy, phẩm chất & domain
    "technical_skill_match": 0.15,  # Kỹ năng kỹ thuật chuẩn hóa (Canonical Taxonomy)
    "project_relevance": 0.20,      # Độ liên quan và bằng chứng dự án
    "experience_relevance": 0.10,   # Kinh nghiệm thực tế (NOT_REQUIRED -> 1.0)
    "education_match": 0.05,        # Bằng cấp, chuyên ngành, trạng thái sinh viên
    "seniority_match": 0.05,        # Cấp bậc mục tiêu (độc lập với số năm kinh nghiệm)
    "work_fit": 0.15,               # Địa điểm, hình thức làm việc, ca làm việc
}

SIGNAL_WEIGHTS = SCORING_WEIGHTS

assert abs(sum(SCORING_WEIGHTS.values()) - 1.0) < 1e-9, "Tổng trọng số các tín hiệu phải bằng 1.0"


# Ma trận tương thích cấp bậc độc lập
SENIORITY_MATRIX: Dict[str, Dict[str, float]] = {
    "INTERN": {
        "INTERN": 1.0, "FRESHER": 0.9, "JUNIOR": 0.6, "MID": 0.2,
        "SENIOR": 0.0, "LEAD": 0.0, "MANAGER": 0.0, "UNKNOWN": 0.8,
    },
    "FRESHER": {
        "INTERN": 0.8, "FRESHER": 1.0, "JUNIOR": 0.8, "MID": 0.3,
        "SENIOR": 0.0, "LEAD": 0.0, "MANAGER": 0.0, "UNKNOWN": 0.8,
    },
    "JUNIOR": {
        "INTERN": 0.5, "FRESHER": 0.7, "JUNIOR": 1.0, "MID": 0.7,
        "SENIOR": 0.2, "LEAD": 0.0, "MANAGER": 0.0, "UNKNOWN": 0.8,
    },
    "MID": {
        "INTERN": 0.1, "FRESHER": 0.2, "JUNIOR": 0.6, "MID": 1.0,
        "SENIOR": 0.7, "LEAD": 0.3, "MANAGER": 0.1, "UNKNOWN": 0.7,
    },
    "SENIOR": {
        "INTERN": 0.0, "FRESHER": 0.0, "JUNIOR": 0.2, "MID": 0.6,
        "SENIOR": 1.0, "LEAD": 0.8, "MANAGER": 0.5, "UNKNOWN": 0.7,
    },
    "UNKNOWN": {
        "INTERN": 0.8, "FRESHER": 0.8, "JUNIOR": 0.8, "MID": 0.8,
        "SENIOR": 0.8, "LEAD": 0.8, "MANAGER": 0.8, "UNKNOWN": 0.8,
    },
}


# ==============================================================================
# Helper Signal Computers
# ==============================================================================

def compute_technical_skill_signal(
    candidate: CandidateProfileDTO,
    job: JobMatchInputDTO,
) -> Tuple[MatchSignal, SkillMatchResult]:
    """
    Tính điểm so khớp kỹ năng kỹ thuật chuẩn hóa (Canonical Taxonomy).
    Nếu JD không yêu cầu kỹ năng kỹ thuật cụ thể -> NOT_REQUIRED, không phạt điểm.
    """
    if not job.required_skills and not job.preferred_skills:
        skill_match = SkillMatchResult(
            matched_required=[],
            missing_required=[],
            matched_preferred=[],
            missing_preferred=[],
            required_coverage=1.0,
            preferred_coverage=1.0,
            has_technical_requirements=False,
        )
        signal = MatchSignal(
            name="technical_skill_match",
            score=1.0,
            weight=SCORING_WEIGHTS["technical_skill_match"],
            confidence=ConfidenceLevel.HIGH,
            evidence_status=EvidenceStatus.NOT_REQUIRED,
            reason="Tin tuyển dụng không yêu cầu từ khóa kỹ thuật chuyên biệt (tập trung năng lực nền tảng)",
            evidence=[],
        )
        return signal, skill_match

    skill_match = match_skills_deterministic(
        candidate_skills=candidate.all_skills,
        job_required=job.required_skills,
        job_preferred=job.preferred_skills,
    )

    evidences: List[EvidenceItem] = []
    for s in skill_match.matched_required:
        evidences.append(
            EvidenceItem(
                source_type="SKILL",
                source_id="technical_skills",
                title=f"Kỹ năng bắt buộc: {s}",
                excerpt=f"Hồ sơ sở hữu kỹ năng chuẩn hóa '{s}'",
            )
        )

    # Tính điểm: Required chiếm 75%, Preferred chiếm 25%
    if job.required_skills and job.preferred_skills:
        score = (skill_match.required_coverage * 0.75) + (skill_match.preferred_coverage * 0.25)
    elif job.required_skills:
        score = skill_match.required_coverage
    else:
        score = skill_match.preferred_coverage

    if skill_match.required_coverage >= 0.7:
        ev_status = EvidenceStatus.SUPPORTED
        reason = f"Đáp ứng {len(skill_match.matched_required)}/{len(job.required_skills)} kỹ năng bắt buộc"
    elif skill_match.required_coverage == 0.0 and len(job.required_skills) > 0:
        ev_status = EvidenceStatus.MISMATCH
        reason = f"Chưa có kỹ năng bắt buộc nào ({', '.join(job.required_skills[:3])})"
    else:
        ev_status = EvidenceStatus.INSUFFICIENT_EVIDENCE
        reason = f"Đáp ứng một phần ({len(skill_match.matched_required)}/{len(job.required_skills)}) kỹ năng bắt buộc"

    signal = MatchSignal(
        name="technical_skill_match",
        score=round(score, 4),
        weight=SCORING_WEIGHTS["technical_skill_match"],
        confidence=ConfidenceLevel.HIGH,
        evidence_status=ev_status,
        reason=reason,
        evidence=evidences[:6],
    )
    return signal, skill_match


def compute_experience_signal(
    candidate: CandidateProfileDTO,
    job: JobMatchInputDTO,
) -> MatchSignal:
    """
    Tính điểm kinh nghiệm chuyên môn.
    Nếu JD không yêu cầu kinh nghiệm -> NOT_REQUIRED -> score = 1.0.
    """
    job_text = f"{job.title} {job.description} {job.requirements_summary or ''}".lower()
    
    is_explicit_no_exp_required = bool(
        job.level == JobLevelEnum.INTERN
        or "không yêu cầu kinh nghiệm" in job_text
        or "no experience required" in job_text
        or "chưa có kinh nghiệm" in job_text
        or "không cần kinh nghiệm" in job_text
        or "fresh graduate" in job_text
    )

    evidences: List[EvidenceItem] = []
    for exp in candidate.experiences:
        evidences.append(
            EvidenceItem(
                source_type="EXPERIENCE",
                source_id=exp.company,
                title=f"{exp.role} tại {exp.company}",
                excerpt=exp.description or "Kinh nghiệm làm việc thực tế",
            )
        )

    if is_explicit_no_exp_required:
        if candidate.experiences:
            reason = "Vị trí không yêu cầu kinh nghiệm, ứng viên có thêm kinh nghiệm thực tế là điểm cộng"
        else:
            reason = "Vị trí không yêu cầu kinh nghiệm chuyên môn (hoàn toàn phù hợp với Thực tập sinh)"
        return MatchSignal(
            name="experience_relevance",
            score=1.0,
            weight=SCORING_WEIGHTS["experience_relevance"],
            confidence=ConfidenceLevel.HIGH,
            evidence_status=EvidenceStatus.NOT_REQUIRED,
            reason=reason,
            evidence=evidences,
        )

    # Job có yêu cầu kinh nghiệm
    if not candidate.experiences:
        # Kiểm tra xem job có đòi hỏi nhiều năm không
        years_match = re.search(r"(\d+)[\+]?\s*(năm|year)", job_text)
        if years_match and int(years_match.group(1)) >= 2:
            return MatchSignal(
                name="experience_relevance",
                score=0.2,
                weight=SCORING_WEIGHTS["experience_relevance"],
                confidence=ConfidenceLevel.HIGH,
                evidence_status=EvidenceStatus.MISMATCH,
                reason=f"Công việc yêu cầu {years_match.group(1)} năm kinh nghiệm nhưng ứng viên chưa có lịch sử làm việc",
                evidence=[],
            )
        return MatchSignal(
            name="experience_relevance",
            score=0.5,
            weight=SCORING_WEIGHTS["experience_relevance"],
            confidence=ConfidenceLevel.INSUFFICIENT_EVIDENCE,
            reason="Hồ sơ chưa có lịch sử làm việc chính thức (INSUFFICIENT_EVIDENCE)",
            evidence=[],
        )

    return MatchSignal(
        name="experience_relevance",
        score=0.9,
        weight=SCORING_WEIGHTS["experience_relevance"],
        confidence=ConfidenceLevel.HIGH,
        evidence_status=EvidenceStatus.SUPPORTED,
        reason=f"Ứng viên có {len(candidate.experiences)} vị trí làm việc thực tế",
        evidence=evidences,
    )


def compute_education_signal(
    candidate: CandidateProfileDTO,
    job: JobMatchInputDTO,
) -> MatchSignal:
    """
    Tính điểm học vấn / bằng cấp.
    Đánh giá dựa trên yêu cầu của JD (Đại học / Chuyên ngành CNTT).
    """
    if not candidate.education:
        return MatchSignal(
            name="education_match",
            score=0.5,
            weight=SCORING_WEIGHTS["education_match"],
            confidence=ConfidenceLevel.INSUFFICIENT_EVIDENCE,
            evidence_status=EvidenceStatus.INSUFFICIENT_EVIDENCE,
            reason="Hồ sơ chưa cập nhật thông tin học vấn",
            evidence=[],
        )

    top_edu = candidate.education[0]
    evidences = [
        EvidenceItem(
            source_type="EDUCATION",
            source_id=top_edu.institution,
            title=f"{top_edu.degree} {top_edu.field} tại {top_edu.institution}",
            excerpt=f"Dự kiến tốt nghiệp {top_edu.graduation_year or '2026'}, GPA: {top_edu.gpa or 'N/A'}",
        )
    ]

    job_text = f"{job.title} {job.description} {job.requirements_summary or ''}".lower()
    
    # Kiểm tra yêu cầu đại học / sinh viên
    is_uni_required = bool(
        "đại học" in job_text or "university" in job_text or "bachelor" in job_text or "sinh viên" in job_text
    )

    is_it_field = any(
        k in (top_edu.field or "").lower()
        for k in ["computer science", "khoa học máy tính", "cyber security", "an toàn thông tin", "công nghệ thông tin", "software"]
    )

    if is_it_field:
        reason = f"Đang theo học {top_edu.degree} ngành {top_edu.field} tại {top_edu.institution} (hoàn toàn tương thích)"
        score = 1.0
        status = EvidenceStatus.SUPPORTED
    elif is_uni_required:
        reason = f"Đang theo học {top_edu.degree} tại {top_edu.institution}"
        score = 0.8
        status = EvidenceStatus.SUPPORTED
    else:
        reason = "Học vấn phù hợp với yêu cầu tuyển dụng"
        score = 1.0
        status = EvidenceStatus.SUPPORTED

    return MatchSignal(
        name="education_match",
        score=round(score, 4),
        weight=SCORING_WEIGHTS["education_match"],
        confidence=ConfidenceLevel.HIGH,
        evidence_status=status,
        reason=reason,
        evidence=evidences,
    )


def infer_candidate_level(candidate: CandidateProfileDTO) -> str:
    """Suy luận cấp bậc của ứng viên từ target_roles và headline."""
    target_roles_text = " ".join(candidate.target_roles).lower() if candidate.target_roles else ""
    headline_text = (candidate.headline or "").lower()
    combined_roles = f"{target_roles_text} {headline_text}"

    return "INTERN" if "intern" in combined_roles or "thực tập" in combined_roles else \
           "FRESHER" if "fresher" in combined_roles else \
           "JUNIOR" if "junior" in combined_roles else \
           "SENIOR" if "senior" in combined_roles else \
           "LEAD" if "lead" in combined_roles else "UNKNOWN"


def compute_seniority_signal(
    candidate: CandidateProfileDTO,
    job: JobMatchInputDTO,
) -> MatchSignal:
    """
    Tính điểm tương thích cấp bậc độc lập với số năm kinh nghiệm.
    """
    cand_level = infer_candidate_level(candidate)


    job_level_str = job.level.value if isinstance(job.level, JobLevelEnum) else str(job.level)
    level_matrix = SENIORITY_MATRIX.get(cand_level, SENIORITY_MATRIX["UNKNOWN"])
    score = level_matrix.get(job_level_str, 0.7)

    return MatchSignal(
        name="seniority_match",
        score=round(score, 4),
        weight=SCORING_WEIGHTS["seniority_match"],
        confidence=ConfidenceLevel.HIGH,
        evidence_status=EvidenceStatus.SUPPORTED if score >= 0.6 else EvidenceStatus.MISMATCH,
        reason=f"Cấp bậc ứng viên ({cand_level}) so với tin tuyển dụng ({job_level_str}) đạt {(score * 100):.0f}% tương thích",
        evidence=[],
    )


def compute_work_fit_signal(
    candidate: CandidateProfileDTO,
    job: JobMatchInputDTO,
) -> MatchSignal:
    """
    Tính điểm phù hợp điều kiện làm việc (Work Fit): Địa điểm, hình thức làm việc, ca làm việc (schedule).
    """
    job_loc_norm = normalize_city_name(job.normalized_location or job.location)
    cand_loc_norm = normalize_city_name(candidate.location)
    cand_target_cities = {normalize_city_name(t) for t in candidate.target_locations if t}

    # 1. Location match
    is_city_matched = (
        job.work_mode == WorkModeEnum.REMOTE
        or (job_loc_norm and job_loc_norm in cand_target_cities)
        or (job_loc_norm and job_loc_norm == cand_loc_norm)
        or any(job_loc_norm in t for t in cand_target_cities if t and job_loc_norm)
        or any(t in job_loc_norm for t in cand_target_cities if t and job_loc_norm)
    )

    # 2. Schedule & Commute
    job_text = f"{job.title} {job.description}".lower()
    has_specific_schedule = bool(re.search(r"\b(\d{1,2}[:h]\d{2})\b", job_text) or "thứ hai" in job_text or "mon" in job_text)
    
    evidences: List[EvidenceItem] = []
    if is_city_matched:
        evidences.append(
            EvidenceItem(
                source_type="PREFERENCE",
                source_id="location",
                title="Khu vực làm việc",
                excerpt=f"Ứng viên tại {candidate.location or 'Hồ Chí Minh'} sẵn sàng làm việc tại {job.normalized_location or job.location or 'khu vực này'}",
            )
        )

    if not is_city_matched:
        score = 0.2
        ev_status = EvidenceStatus.MISMATCH
        reason = f"Địa điểm ({job.normalized_location or job.location}) ngoài khu vực mục tiêu của ứng viên"
    elif has_specific_schedule:
        # Thành phố khớp, ca làm việc cần xác nhận thêm với ứng viên
        score = 0.90
        ev_status = EvidenceStatus.SUPPORTED
        reason = f"Địa điểm ({job.normalized_location or job.location}) tương thích; ca làm việc cụ thể trong JD cần xác nhận thời gian biểu"
    else:
        score = 1.0
        ev_status = EvidenceStatus.SUPPORTED
        reason = f"Địa điểm ({job.normalized_location or job.location}) và hình thức ({job.work_mode.value}) hoàn toàn phù hợp"

    return MatchSignal(
        name="work_fit",
        score=round(score, 4),
        weight=SCORING_WEIGHTS["work_fit"],
        confidence=ConfidenceLevel.HIGH if is_city_matched else ConfidenceLevel.MEDIUM,
        evidence_status=ev_status,
        reason=reason,
        evidence=evidences,
    )


# ==============================================================================
# Pure Matching Engine Orchestrator
# ==============================================================================

def calculate_match_score(
    candidate: CandidateProfileDTO,
    job: JobMatchInputDTO,
    project_embeddings: Optional[List[List[float]]] = None,
    skill_match: Optional[SkillMatchResult] = None,
    project_relevance: Optional[float] = None,
) -> MatchScoreResult:
    """
    Hàm thuần khiết (Pure Matching Engine) tính toán điểm số và phân loại tư cách:
    1. Đánh giá 4 Hard Filters tri-state -> Eligibility (ELIGIBLE / BLOCKED / UNCERTAIN).
    2. Đánh giá 7 Tín hiệu thành phần với Requirement & Evidence Layer.
    3. Tính điểm số 0 - 100 theo công thức: Score = sum(weight_i * score_i) * 100.
    4. Áp dụng Smart Score Cap (chỉ cap khi JD thực sự có technical required skills).
    5. Phân loại Recommendation Category.
    """
    # 1. Hard filters
    hard_filter_results = evaluate_hard_filters(candidate, job)
    eligibility = derive_eligibility(hard_filter_results)

    eligibility_reasons: List[str] = [
        f"{r.filter.upper()}: {r.reason}"
        for r in hard_filter_results
        if r.status in (FilterStatus.FAIL, FilterStatus.UNKNOWN)
    ]

    # 2. 7 Signals
    # Signal 1: Requirement / Competency Fit (30%)
    req_signal, req_evaluations = requirement_matcher.evaluate(candidate, job)

    # Signal 2: Technical Skill Match (15%)
    if skill_match is not None:
        if job.required_skills and job.preferred_skills:
            tech_score = (skill_match.required_coverage * 0.75) + (skill_match.preferred_coverage * 0.25)
        elif job.required_skills:
            tech_score = skill_match.required_coverage
        else:
            tech_score = skill_match.preferred_coverage
        tech_signal = MatchSignal(
            name="technical_skill_match",
            score=round(tech_score, 4),
            weight=SCORING_WEIGHTS["technical_skill_match"],
            confidence=ConfidenceLevel.HIGH,
            evidence_status=EvidenceStatus.SUPPORTED if skill_match.required_coverage >= 0.7 else EvidenceStatus.INSUFFICIENT_EVIDENCE,
            reason=f"Độ phủ kỹ năng bắt buộc: {(skill_match.required_coverage * 100):.1f}%",
        )
    else:
        tech_signal, skill_match = compute_technical_skill_signal(candidate, job)

    # Signal 3: Project Relevance (20%)
    if project_relevance is not None:
        proj_score = project_relevance
        proj_conf = ConfidenceLevel.HIGH
        proj_reason = f"Độ phù hợp dự án đạt {(project_relevance * 100):.1f}%"
        proj_evidences = []
    else:
        proj_score, proj_conf, proj_reason, proj_evidences = compute_project_relevance(
            candidate, job, project_embeddings
        )

    proj_signal = MatchSignal(
        name="project_relevance",
        score=proj_score,
        weight=SCORING_WEIGHTS["project_relevance"],
        confidence=proj_conf,
        evidence_status=EvidenceStatus.SUPPORTED if proj_score >= 0.7 else EvidenceStatus.INSUFFICIENT_EVIDENCE,
        reason=proj_reason,
        evidence=proj_evidences,
    )

    # Signal 4: Experience Relevance (10%)

    exp_signal = compute_experience_signal(candidate, job)

    # Signal 5: Education Match (5%)
    edu_signal = compute_education_signal(candidate, job)

    # Signal 6: Seniority Match (5%)
    seniority_signal = compute_seniority_signal(candidate, job)

    # Signal 7: Work Fit (15%)
    work_fit_signal = compute_work_fit_signal(candidate, job)

    signals: List[MatchSignal] = [
        req_signal,
        tech_signal,
        proj_signal,
        exp_signal,
        edu_signal,
        seniority_signal,
        work_fit_signal,
    ]

    # 3. Tính Weighted Score (0 - 100)
    raw_score = sum(s.weight * s.score for s in signals) * 100.0
    final_score = round(raw_score, 2)
    final_score = max(0.0, min(100.0, final_score))

    # 4. Smart Score Cap Rule
    warnings: List[str] = []
    # Chỉ áp dụng trần điểm khi JD thực sự có yêu cầu kỹ thuật bắt buộc
    if (
        skill_match.has_technical_requirements
        and len(job.required_skills) > 0
        and skill_match.required_coverage < 0.3
    ):
        if final_score > 50.0:
            final_score = 50.0
            warnings.append(
                f"Điểm số bị giới hạn tối đa 50.0 do độ phủ kỹ năng bắt buộc ({(skill_match.required_coverage * 100):.1f}%) dưới 30%"
            )

    # 5. Recommendation
    recommendation = derive_recommendation(final_score, eligibility)

    return MatchScoreResult(
        score=final_score,
        eligibility=eligibility,
        eligibility_reasons=eligibility_reasons,
        recommendation=recommendation,
        signals=signals,
        hard_filter_results=hard_filter_results,
        skill_match=skill_match,
        requirement_evaluations=req_evaluations,
        scoring_version="v2",
        taxonomy_version="v1",
        warnings=warnings,
    )
