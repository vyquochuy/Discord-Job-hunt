import re
from typing import List, Optional, Set
from app.models.job import JobLevelEnum, WorkModeEnum
from app.services.matching.models import (
    CandidateProfileDTO,
    Eligibility,
    FilterStatus,
    HardFilterResult,
    JobMatchInputDTO,
    RecommendationCategory,
)


def normalize_city_name(text: Optional[str]) -> str:
    """Chuẩn hóa tên thành phố để so khớp (lowercase, loại bỏ tiền tố quận/thành phố)."""
    if not text:
        return ""
    cleaned = text.lower().strip()
    cleaned = re.sub(r"\b(tp\.?|thành phố|tỉnh|district|quận|huyện|q\.)\b", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if any(k in cleaned for k in ["ho chi minh", "hcm", "sài gòn", "saigon", "thủ đức", "thu duc", "long bình", "long binh"]):
        return "ho chi minh"
    if any(k in cleaned for k in ["ha noi", "hanoi", "hn"]):
        return "hanoi"
    if any(k in cleaned for k in ["da nang", "danang"]):
        return "da nang"
    return cleaned


def evaluate_hard_filters(
    candidate: CandidateProfileDTO,
    job: JobMatchInputDTO,
) -> List[HardFilterResult]:
    """
    Thực thi 4 bộ lọc cứng (Hard Filters) hoàn toàn Deterministic theo Tri-State (PASS / FAIL / UNKNOWN).
    """
    results: List[HardFilterResult] = []

    # =========================================================================
    # 1. Work Mode Filter
    # =========================================================================
    cand_pref_raw = candidate.preferences.get("remote") if candidate.preferences else None
    cand_pref = str(cand_pref_raw).lower().strip() if cand_pref_raw is not None else ""
    cand_targets_lower = [t.lower() for t in candidate.target_locations]

    has_physical_target_city = any(
        t for t in cand_targets_lower if t not in ("remote", "hybrid", "")
    )
    is_strict_remote_only = (
        (cand_pref == "remote" and not has_physical_target_city)
        or (cand_targets_lower == ["remote"])
    )

    if not cand_pref and not candidate.target_locations:
        work_mode_status = FilterStatus.UNKNOWN
        work_mode_reason = "Ứng viên chưa thiết lập hình thức làm việc mong muốn"
    elif is_strict_remote_only:
        if job.work_mode == WorkModeEnum.REMOTE:
            work_mode_status = FilterStatus.PASS
            work_mode_reason = "Công việc hỗ trợ làm việc từ xa (100% Remote) đúng nguyện vọng"
        elif job.work_mode == WorkModeEnum.HYBRID:
            work_mode_status = FilterStatus.PASS
            work_mode_reason = "Công việc Hybrid linh hoạt phù hợp"
        else:  # ONSITE
            work_mode_status = FilterStatus.FAIL
            work_mode_reason = "Ứng viên chỉ tìm việc từ xa (Remote-only) nhưng công việc yêu cầu Onsite tại văn phòng"
    else:
        work_mode_status = FilterStatus.PASS
        work_mode_reason = f"Hình thức làm việc ({job.work_mode.value}) phù hợp với khu vực làm việc của ứng viên"



    results.append(
        HardFilterResult(
            filter="work_mode",
            status=work_mode_status,
            reason=work_mode_reason,
        )
    )

    # =========================================================================
    # 2. Location Filter
    # =========================================================================
    if job.work_mode == WorkModeEnum.REMOTE:
        loc_status = FilterStatus.PASS
        loc_reason = "Công việc từ xa (Remote), không bị giới hạn bởi vị trí địa lý"
    elif not job.location and not job.normalized_location:
        loc_status = FilterStatus.UNKNOWN
        loc_reason = "Tin tuyển dụng không nêu rõ địa điểm làm việc cụ thể"
    elif not candidate.target_locations and not candidate.location:
        loc_status = FilterStatus.UNKNOWN
        loc_reason = "Ứng viên chưa thiết lập địa điểm làm việc mong muốn"
    else:
        job_loc_norm = normalize_city_name(job.normalized_location or job.location)
        cand_loc_norm = normalize_city_name(candidate.location)
        cand_target_cities = {normalize_city_name(t) for t in candidate.target_locations if t}

        is_city_matched = (
            (job_loc_norm and job_loc_norm in cand_target_cities)
            or (job_loc_norm and job_loc_norm == cand_loc_norm)
            or any(job_loc_norm in t for t in cand_target_cities if t and job_loc_norm)
            or any(t in job_loc_norm for t in cand_target_cities if t and job_loc_norm)
        )

        if is_city_matched:
            loc_status = FilterStatus.PASS
            loc_reason = f"Địa điểm ({job.normalized_location or job.location}) thuộc khu vực mục tiêu của ứng viên"
        elif job.work_mode == WorkModeEnum.HYBRID:
            loc_status = FilterStatus.UNKNOWN
            loc_reason = f"Địa điểm ({job.normalized_location or job.location}) khác khu vực mục tiêu nhưng hỗ trợ Hybrid"
        else:  # ONSITE
            loc_status = FilterStatus.FAIL
            loc_reason = f"Công việc yêu cầu Onsite tại '{job.normalized_location or job.location}', nằm ngoài khu vực mục tiêu của ứng viên"

    results.append(
        HardFilterResult(
            filter="location",
            status=loc_status,
            reason=loc_reason,
        )
    )

    # =========================================================================
    # 3. Seniority & Employer Exclusions Filter
    # =========================================================================
    target_roles_text = " ".join(candidate.target_roles).lower() if candidate.target_roles else ""
    headline_text = (candidate.headline or "").lower()
    combined_roles = f"{target_roles_text} {headline_text}"

    is_intern = any(kw in combined_roles for kw in ["intern", "internship", "thực tập"])
    is_fresher = any(kw in combined_roles for kw in ["fresher", "mới tốt nghiệp", "trainee"]) and not is_intern
    is_senior_lead = any(kw in combined_roles for kw in ["senior", "lead", "principal", "manager", "architect"]) and not is_intern

    job_text = f"{job.title} {job.description} {job.requirements_summary or ''}".lower()
    
    # Kiểm tra explicit exclusion từ phía nhà tuyển dụng (ví dụ: "chỉ tuyển intern, không tuyển fresher/junior")
    has_strict_intern_only_policy = bool(
        re.search(r"chỉ tuyển\s+(intern|thực tập)", job_text, re.IGNORECASE)
        or re.search(r"không tuyển\s+(fresher|junior)", job_text, re.IGNORECASE)
    )

    if has_strict_intern_only_policy:
        if is_intern:
            seniority_status = FilterStatus.PASS
            seniority_reason = "Ứng viên là Thực tập sinh (Intern) đáp ứng đúng chính sách chỉ tuyển Intern của công ty"
        else:
            seniority_status = FilterStatus.FAIL
            seniority_reason = "Doanh nghiệp có chính sách nghiêm ngặt chỉ tuyển Intern (loại trừ Fresher/Junior)"
    elif is_intern:
        if job.level in (JobLevelEnum.SENIOR, JobLevelEnum.LEAD, JobLevelEnum.MANAGER):
            seniority_status = FilterStatus.FAIL
            seniority_reason = f"Cấp bậc yêu cầu ({job.level.value}) vượt quá xa mục tiêu của ứng viên Intern"
        else:
            seniority_status = FilterStatus.PASS
            seniority_reason = f"Cấp bậc ({job.level.value}) phù hợp với ứng viên Intern"
    elif is_senior_lead:
        if job.level == JobLevelEnum.INTERN:
            seniority_status = FilterStatus.FAIL
            seniority_reason = "Vị trí Thực tập sinh (Intern) không phù hợp với ứng viên cấp bậc Senior/Lead"
        else:
            seniority_status = FilterStatus.PASS
            seniority_reason = f"Cấp bậc ({job.level.value}) phù hợp"
    else:
        # Fresher / Junior / Mid
        if job.level == JobLevelEnum.LEAD or job.level == JobLevelEnum.MANAGER:
            seniority_status = FilterStatus.FAIL
            seniority_reason = f"Cấp bậc ({job.level.value}) vượt quá mục tiêu hiện tại"
        else:
            seniority_status = FilterStatus.PASS
            seniority_reason = f"Cấp bậc ({job.level.value}) nằm trong ngưỡng xem xét"

    results.append(
        HardFilterResult(
            filter="seniority",
            status=seniority_status,
            reason=seniority_reason,
        )
    )

    # =========================================================================
    # 4. Salary Filter
    # =========================================================================
    min_sal_raw = candidate.preferences.get("minimum_salary") if candidate.preferences else None
    min_sal_pref = None
    if isinstance(min_sal_raw, dict):
        val = min_sal_raw.get("value")
        if isinstance(val, (int, float)):
            min_sal_pref = float(val)
    elif isinstance(min_sal_raw, (int, float)):
        min_sal_pref = float(min_sal_raw)

    if min_sal_pref is None or min_sal_pref <= 0:
        sal_status = FilterStatus.UNKNOWN
        sal_reason = "Ứng viên không đặt mức lương tối thiểu"
    elif job.is_salary_negotiable or (job.max_salary is None and job.min_salary is None):
        sal_status = FilterStatus.UNKNOWN
        sal_reason = "Mức lương thỏa thuận hoặc chưa công bố cụ thể trong JD"
    elif job.max_salary is not None:
        if job.max_salary >= min_sal_pref:
            sal_status = FilterStatus.PASS
            sal_reason = f"Mức lương tối đa ({job.max_salary:,.0f} {job.salary_currency or ''}) đáp ứng kỳ vọng ({min_sal_pref:,.0f})"
        else:
            sal_status = FilterStatus.FAIL
            sal_reason = f"Mức lương tối đa ({job.max_salary:,.0f} {job.salary_currency or ''}) thấp hơn kỳ vọng tối thiểu ({min_sal_pref:,.0f})"
    else:
        sal_status = FilterStatus.UNKNOWN
        sal_reason = "Thông tin lương chưa đầy đủ để đối soát"

    results.append(
        HardFilterResult(
            filter="salary",
            status=sal_status,
            reason=sal_reason,
        )
    )

    return results


def derive_eligibility(results: List[HardFilterResult]) -> Eligibility:
    """
    Xác định tư cách ứng tuyển:
    - BLOCKED: Nếu có bất kỳ filter nào bị FAIL.
    - UNCERTAIN: Nếu không có FAIL, nhưng có >= 2 UNKNOWN.
    - ELIGIBLE: Nếu tất cả PASS hoặc chỉ có <= 1 UNKNOWN.
    """
    statuses = [r.status for r in results]
    if FilterStatus.FAIL in statuses:
        return Eligibility.BLOCKED
    unknown_count = statuses.count(FilterStatus.UNKNOWN)
    if unknown_count >= 2:
        return Eligibility.UNCERTAIN
    return Eligibility.ELIGIBLE


def derive_recommendation(score: float, eligibility: Eligibility) -> RecommendationCategory:
    """
    Phân loại khuyến nghị ứng tuyển hoàn toàn tách biệt:
    - Nếu BLOCKED -> DO_NOT_APPLY (bất kể điểm)
    - Nếu UNCERTAIN và điểm >= 60 -> REVIEW_REQUIRED
    - Nếu ELIGIBLE:
      + score >= 80 -> STRONG_MATCH
      + score >= 60 -> GOOD_MATCH
      + score >= 40 -> WEAK_MATCH
      + score < 40  -> POOR_MATCH
    """
    if eligibility == Eligibility.BLOCKED:
        return RecommendationCategory.DO_NOT_APPLY
    if eligibility == Eligibility.UNCERTAIN and score >= 60.0:
        return RecommendationCategory.REVIEW_REQUIRED
    if score >= 80.0:
        return RecommendationCategory.STRONG_MATCH
    if score >= 60.0:
        return RecommendationCategory.GOOD_MATCH
    if score >= 40.0:
        return RecommendationCategory.WEAK_MATCH
    return RecommendationCategory.POOR_MATCH
