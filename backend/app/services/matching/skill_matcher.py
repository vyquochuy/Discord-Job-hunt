from typing import List, Optional, Set
from app.services.matching.models import SkillMatchResult
from app.services.normalization.skill_normalizer import SkillNormalizer, skill_normalizer


def canonicalize_skills(
    raw_skills: List[str], normalizer: Optional[SkillNormalizer] = None
) -> Set[str]:
    """
    Chuẩn hóa và gom nhóm danh sách kỹ năng về Canonical Names (loại bỏ biến thể và trùng lặp).
    Ví dụ: ['Python', 'python3', 'py'] -> {'Python'}
    """
    norm = normalizer or skill_normalizer
    canonical_set: Set[str] = set()

    for s in raw_skills:
        if not s or not s.strip():
            continue
        canonical_name, _ = norm.normalize_skill(s.strip())
        if canonical_name:
            canonical_set.add(canonical_name)

    return canonical_set


def match_skills(
    candidate_skills: List[str],
    job_required: List[str],
    job_preferred: List[str],
    normalizer: Optional[SkillNormalizer] = None,
) -> SkillMatchResult:
    """
    So khớp kỹ năng hoàn toàn chuẩn xác (Deterministic) dựa trên Canonical Taxonomy & Alias Dictionary.
    Tuyệt đối không dùng embedding để tránh false positives (ví dụ C# != C++).
    """
    norm = normalizer or skill_normalizer

    candidate_canonical = canonicalize_skills(candidate_skills, norm)
    job_req_canonical = canonicalize_skills(job_required, norm)
    job_pref_canonical = canonicalize_skills(job_preferred, norm)

    # 1. Required Skills
    matched_req = sorted(list(job_req_canonical & candidate_canonical))
    missing_req = sorted(list(job_req_canonical - candidate_canonical))

    if len(job_req_canonical) == 0:
        req_coverage = 1.0  # Không có yêu cầu bắt buộc -> không phạt
    else:
        req_coverage = len(matched_req) / len(job_req_canonical)

    # 2. Preferred Skills
    matched_pref = sorted(list(job_pref_canonical & candidate_canonical))
    missing_pref = sorted(list(job_pref_canonical - candidate_canonical))

    if len(job_pref_canonical) == 0:
        pref_coverage = 1.0  # Không có yêu cầu ưu tiên -> full điểm
    else:
        pref_coverage = len(matched_pref) / len(job_pref_canonical)

    return SkillMatchResult(
        matched_required=matched_req,
        missing_required=missing_req,
        matched_preferred=matched_pref,
        missing_preferred=missing_pref,
        required_coverage=round(req_coverage, 4),
        preferred_coverage=round(pref_coverage, 4),
        has_technical_requirements=bool(len(job_req_canonical) > 0 or len(job_pref_canonical) > 0),
    )


match_skills_deterministic = match_skills
