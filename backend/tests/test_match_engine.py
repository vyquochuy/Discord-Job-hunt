import logging
import pytest
import random
from app.models.job import JobLevelEnum, WorkModeEnum
from app.services.matching.hard_filters import (
    derive_eligibility,
    derive_recommendation,
    evaluate_hard_filters,
)
from app.services.matching.models import (
    CandidateEducationDTO,
    CandidateExperienceDTO,
    CandidateProfileDTO,
    CandidateProjectDTO,
    ConfidenceLevel,
    Eligibility,
    FilterStatus,
    HardFilterResult,
    JobMatchInputDTO,
    RecommendationCategory,
    SkillMatchResult,
)
from app.services.matching.scoring_engine import (
    SIGNAL_WEIGHTS,
    calculate_match_score,
    infer_candidate_level,
)
from app.services.matching.skill_matcher import match_skills

logger = logging.getLogger("test_match_engine")


# ==============================================================================
# 1. Invariant Tests (CRITICAL)
# ==============================================================================

def test_signal_weights_sum_to_one():
    """Bắt buộc tổng trọng số của 7 tín hiệu phải tuyệt đối bằng 1.0."""
    logger.info("=== [TEST] Invariant 1: Signal Weights Sum ===")
    total = sum(SIGNAL_WEIGHTS.values())
    logger.info(f"Signal weights: {SIGNAL_WEIGHTS}")
    logger.info(f"Total sum: {total}")
    assert abs(total - 1.0) < 1e-9, f"Weights sum {total} != 1.0"


def test_score_always_in_range_0_to_100():
    """Property test: Điểm số luôn nằm trong đoạn [0.0, 100.0] với mọi tổ hợp ngẫu nhiên."""
    logger.info("=== [TEST] Invariant 2: Score Range [0.0, 100.0] ===")
    random.seed(42)

    candidate = CandidateProfileDTO(
        full_name="Vy Quoc Huy",
        headline="System Intern",
        skills=["Python", "FastAPI", "Docker", "PostgreSQL"],
        target_roles=["System Intern", "Backend Developer"],
        target_locations=["Ho Chi Minh City", "Remote"],
    )

    job = JobMatchInputDTO(
        title="Backend Engineer",
        company_name="Tech Corp",
        location="Ho Chi Minh City",
        work_mode=WorkModeEnum.HYBRID,
        level=JobLevelEnum.JUNIOR,
        required_skills=["Python", "PostgreSQL"],
    )

    for i in range(100):
        req_cov = random.uniform(0.0, 1.0)
        pref_cov = random.uniform(0.0, 1.0)
        proj_rel = random.uniform(0.0, 1.0)

        skill_res = SkillMatchResult(
            matched_required=["Python"],
            missing_required=[],
            required_coverage=req_cov,
            preferred_coverage=pref_cov,
        )

        res = calculate_match_score(
            candidate=candidate,
            job=job,
            skill_match=skill_res,
            project_relevance=proj_rel,
        )

        assert 0.0 <= res.score <= 100.0, f"Score {res.score} out of bounds for iteration {i}"


# ==============================================================================
# 2. Recommendation Boundaries & Eligibility Override Tests
# ==============================================================================

def test_recommendation_boundaries():
    """Kiểm tra chính xác các ngưỡng phân loại khi ELIGIBLE."""
    logger.info("=== [TEST] Recommendation Category Boundaries ===")
    assert derive_recommendation(80.00, Eligibility.ELIGIBLE) == RecommendationCategory.STRONG_MATCH
    assert derive_recommendation(79.99, Eligibility.ELIGIBLE) == RecommendationCategory.GOOD_MATCH
    assert derive_recommendation(60.00, Eligibility.ELIGIBLE) == RecommendationCategory.GOOD_MATCH
    assert derive_recommendation(59.99, Eligibility.ELIGIBLE) == RecommendationCategory.WEAK_MATCH
    assert derive_recommendation(40.00, Eligibility.ELIGIBLE) == RecommendationCategory.WEAK_MATCH
    assert derive_recommendation(39.99, Eligibility.ELIGIBLE) == RecommendationCategory.POOR_MATCH
    assert derive_recommendation(0.00, Eligibility.ELIGIBLE) == RecommendationCategory.POOR_MATCH


def test_eligibility_override_recommendation():
    """Tách biệt Eligibility và Score: BLOCKED -> DO_NOT_APPLY dù điểm cao."""
    logger.info("=== [TEST] Eligibility Override on High Score ===")
    # Điểm 95 nhưng bị BLOCKED (ví dụ lương không thỏa thuận được)
    rec_blocked = derive_recommendation(95.0, Eligibility.BLOCKED)
    assert rec_blocked == RecommendationCategory.DO_NOT_APPLY

    # Điểm 75 nhưng UNCERTAIN (nhiều trường chưa rõ) -> REVIEW_REQUIRED
    rec_uncertain = derive_recommendation(75.0, Eligibility.UNCERTAIN)
    assert rec_uncertain == RecommendationCategory.REVIEW_REQUIRED

    # Điểm 45 và UNCERTAIN -> WEAK_MATCH (không đủ 60 điểm để review)
    rec_weak_uncertain = derive_recommendation(45.0, Eligibility.UNCERTAIN)
    assert rec_weak_uncertain == RecommendationCategory.WEAK_MATCH


# ==============================================================================
# 3. Score Cap Rule Tests (< 30% required skill coverage)
# ==============================================================================

def test_score_cap_rule():
    """Nếu required skill coverage < 30%, điểm số bị giới hạn tối đa 50.0."""
    logger.info("=== [TEST] Score Cap Rule on Skill Failure ===")
    candidate = CandidateProfileDTO(
        full_name="Vy Quoc Huy",
        headline="System Intern",
        skills=["Python"],
        target_roles=["System Intern"],
        target_locations=["Ho Chi Minh City"],
        education=[CandidateEducationDTO(institution="USSH", degree="Bachelor")],
    )

    job = JobMatchInputDTO(
        title="Senior Tech Lead",
        company_name="VNG",
        location="Ho Chi Minh City",
        work_mode=WorkModeEnum.ONSITE,
        level=JobLevelEnum.INTERN,
        required_skills=["C++", "Rust", "Go", "Java", "Python"],
    )

    # Case 1: required coverage = 0.20 (1/5 skills) -> Score phải bị cap ở <= 50.0
    skill_match_low = SkillMatchResult(
        matched_required=["Python"],
        missing_required=["C++", "Rust", "Go", "Java"],
        required_coverage=0.20,
        preferred_coverage=1.0,
    )

    res_capped = calculate_match_score(
        candidate=candidate,
        job=job,
        skill_match=skill_match_low,
        project_relevance=1.0,  # Dự án điểm rất cao 1.0
    )
    logger.info(f"Capped result: Score={res_capped.score}, Warnings={res_capped.warnings}")
    assert res_capped.score <= 50.0
    assert any("30%" in w for w in res_capped.warnings)

    # Case 2: required coverage = 0.30 (đúng 30%) -> Không bị cap
    skill_match_30 = SkillMatchResult(
        matched_required=["Python", "Go", "Java"],
        missing_required=["C++", "Rust"],
        required_coverage=0.30,
        preferred_coverage=1.0,
    )
    res_no_cap = calculate_match_score(
        candidate=candidate,
        job=job,
        skill_match=skill_match_30,
        project_relevance=1.0,
    )
    assert res_no_cap.score > 50.0


# ==============================================================================
# 4. Tri-State Hard Filter Tests
# ==============================================================================

def test_hard_filter_work_mode():
    """Kiểm tra logic lọc hình thức làm việc (Tri-state)."""
    # Ứng viên chỉ muốn Remote
    cand_remote = CandidateProfileDTO(
        target_locations=["Remote"],
        preferences={"remote": "remote"},
    )
    job_remote = JobMatchInputDTO(title="Dev", company_name="A", work_mode=WorkModeEnum.REMOTE)
    job_onsite = JobMatchInputDTO(title="Dev", company_name="A", work_mode=WorkModeEnum.ONSITE)
    job_hybrid = JobMatchInputDTO(title="Dev", company_name="A", work_mode=WorkModeEnum.HYBRID)

    filters_remote = evaluate_hard_filters(cand_remote, job_remote)
    assert next(f for f in filters_remote if f.filter == "work_mode").status == FilterStatus.PASS

    filters_onsite = evaluate_hard_filters(cand_remote, job_onsite)
    assert next(f for f in filters_onsite if f.filter == "work_mode").status == FilterStatus.FAIL

    filters_hybrid = evaluate_hard_filters(cand_remote, job_hybrid)
    assert next(f for f in filters_hybrid if f.filter == "work_mode").status == FilterStatus.PASS


def test_hard_filter_location():
    """Kiểm tra logic lọc địa điểm."""
    cand = CandidateProfileDTO(
        location="Ho Chi Minh City",
        target_locations=["Ho Chi Minh City"],
    )

    job_hcm = JobMatchInputDTO(
        title="Dev", company_name="A", location="District 1, Ho Chi Minh", work_mode=WorkModeEnum.ONSITE
    )
    job_hn_onsite = JobMatchInputDTO(
        title="Dev", company_name="A", location="Cau Giay, Hanoi", work_mode=WorkModeEnum.ONSITE
    )
    job_hn_hybrid = JobMatchInputDTO(
        title="Dev", company_name="A", location="Cau Giay, Hanoi", work_mode=WorkModeEnum.HYBRID
    )
    job_remote = JobMatchInputDTO(
        title="Dev", company_name="A", location="Singapore", work_mode=WorkModeEnum.REMOTE
    )

    assert next(f for f in evaluate_hard_filters(cand, job_hcm) if f.filter == "location").status == FilterStatus.PASS
    assert next(f for f in evaluate_hard_filters(cand, job_hn_onsite) if f.filter == "location").status == FilterStatus.FAIL
    assert next(f for f in evaluate_hard_filters(cand, job_hn_hybrid) if f.filter == "location").status == FilterStatus.UNKNOWN
    assert next(f for f in evaluate_hard_filters(cand, job_remote) if f.filter == "location").status == FilterStatus.PASS


def test_hard_filter_salary():
    """Kiểm tra logic lọc lương kỳ vọng."""
    cand = CandidateProfileDTO(preferences={"minimum_salary": 20000000})

    job_ok = JobMatchInputDTO(title="Dev", company_name="A", min_salary=15000000, max_salary=25000000)
    job_low = JobMatchInputDTO(title="Dev", company_name="A", min_salary=10000000, max_salary=18000000)
    job_neg = JobMatchInputDTO(title="Dev", company_name="A", is_salary_negotiable=True)
    job_no_info = JobMatchInputDTO(title="Dev", company_name="A")

    assert next(f for f in evaluate_hard_filters(cand, job_ok) if f.filter == "salary").status == FilterStatus.PASS
    assert next(f for f in evaluate_hard_filters(cand, job_low) if f.filter == "salary").status == FilterStatus.FAIL
    assert next(f for f in evaluate_hard_filters(cand, job_neg) if f.filter == "salary").status == FilterStatus.UNKNOWN
    assert next(f for f in evaluate_hard_filters(cand, job_no_info) if f.filter == "salary").status == FilterStatus.UNKNOWN


def test_hard_filter_seniority():
    """Kiểm tra logic lọc cấp bậc (chỉ bắt lỗi cực đoan)."""
    cand_intern = CandidateProfileDTO(target_roles=["System Intern"])
    job_lead = JobMatchInputDTO(title="Tech Lead", company_name="A", level=JobLevelEnum.LEAD)
    job_junior = JobMatchInputDTO(title="Junior Dev", company_name="A", level=JobLevelEnum.JUNIOR)

    assert next(f for f in evaluate_hard_filters(cand_intern, job_lead) if f.filter == "seniority").status == FilterStatus.FAIL
    assert next(f for f in evaluate_hard_filters(cand_intern, job_junior) if f.filter == "seniority").status == FilterStatus.PASS


# ==============================================================================
# 5. Skill Matcher Deduplication & Alias Tests
# ==============================================================================

def test_skill_matcher_deduplication():
    """Job yêu cầu các biến thể của cùng 1 skill, ứng viên có 1 skill -> Coverage = 1.0."""
    logger.info("=== [TEST] Skill Matcher Deduplication & Aliases ===")
    job_req = ["Python", "python3", "Py", "PYTHON"]
    cand_skills = ["Python"]

    res = match_skills(candidate_skills=cand_skills, job_required=job_req, job_preferred=[])
    logger.info(f"Skill Match Result: {res}")
    assert res.matched_required == ["Python"]
    assert res.missing_required == []
    assert res.required_coverage == 1.0


def test_skill_matcher_project_tech_inclusion():
    """Kỹ năng trong dự án của ứng viên được tự động đưa vào tập kỹ năng candidate."""
    cand = CandidateProfileDTO(
        skills=["Python"],
        projects=[
            CandidateProjectDTO(
                name="Project A",
                technologies=["FastAPI", "PostgreSQL", "Docker"],
            )
        ],
    )
    job_req = ["Python", "FastAPI", "Docker"]
    res = match_skills(candidate_skills=cand.all_skills, job_required=job_req, job_preferred=[])
    assert set(res.matched_required) == {"Python", "FastAPI", "Docker"}
    assert res.required_coverage == 1.0


# ==============================================================================
# 6. Independence: Experience Relevance vs Seniority Match
# ==============================================================================

def test_experience_vs_seniority_independence():
    """Đảm bảo tín hiệu kinh nghiệm và tín hiệu cấp bậc không bị chồng chéo hay double-count."""
    logger.info("=== [TEST] Experience vs Seniority Independence ===")
    # Ứng viên chưa có kinh nghiệm đi làm, ứng tuyển Intern -> Seniority 1.0, Experience 1.0 (NOT_REQUIRED)
    cand_fresher = CandidateProfileDTO(
        target_roles=["System Intern"],
        experiences=[],  # Chưa có kinh nghiệm
    )
    job_intern = JobMatchInputDTO(
        title="Intern Dev",
        company_name="A",
        level=JobLevelEnum.INTERN,
    )

    res = calculate_match_score(
        candidate=cand_fresher,
        job=job_intern,
        skill_match=SkillMatchResult(required_coverage=1.0, preferred_coverage=1.0),
    )

    exp_signal = next(s for s in res.signals if s.name == "experience_relevance")
    sen_signal = next(s for s in res.signals if s.name == "seniority_match")

    # Intern job không đòi hỏi kinh nghiệm -> NOT_REQUIRED (1.0)
    assert exp_signal.score == 1.0
    assert exp_signal.evidence_status.value == "NOT_REQUIRED"
    assert sen_signal.score == 1.0

