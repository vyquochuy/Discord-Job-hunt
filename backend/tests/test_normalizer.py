import logging
import pytest
from app.models.job import JobLevelEnum, SkillCategoryEnum, WorkModeEnum
from app.services.normalization.job_normalizer import job_normalizer
from app.services.normalization.skill_normalizer import skill_normalizer

logger = logging.getLogger("test.normalizer")


def test_skill_normalizer_aliases():
    """Kiểm tra SkillNormalizer chuẩn hóa các biến thể về Canonical Name."""
    logger.info("--- [TEST] Skill Normalizer Aliases Mapping ---")
    
    test_cases = [
        ("python3", "Python", SkillCategoryEnum.LANGUAGE),
        ("golang", "Go", SkillCategoryEnum.LANGUAGE),
        ("js", "JavaScript", SkillCategoryEnum.LANGUAGE),
        ("ts", "TypeScript", SkillCategoryEnum.LANGUAGE),
        ("postgres", "PostgreSQL", SkillCategoryEnum.DATABASE),
        ("pgsql", "PostgreSQL", SkillCategoryEnum.DATABASE),
        ("mongo db", "MongoDB", SkillCategoryEnum.DATABASE),
        ("nodejs", "Node.js", SkillCategoryEnum.FRAMEWORK),
        ("fastapi", "FastAPI", SkillCategoryEnum.FRAMEWORK),
        ("amazon web services", "AWS", SkillCategoryEnum.CLOUD),
        ("k8s", "Kubernetes", SkillCategoryEnum.TOOL),
    ]

    for raw, expected_canonical, expected_cat in test_cases:
        canonical, category = skill_normalizer.normalize_skill(raw)
        logger.info(f"  Mapping: '{raw}' -> Canonical: '{canonical}' (Category: {category.value})")
        assert canonical == expected_canonical
        assert category == expected_cat


def test_skill_normalizer_deduplication():
    """Kiểm tra hàm normalize_skills loại bỏ trùng lặp ngữ nghĩa."""
    logger.info("--- [TEST] Skill Normalizer Deduplication ---")
    raw_list = ["Python", "python3", "py", "FastAPI", "fast api", "PostgreSQL", "postgres"]
    logger.info(f"  Input raw skills list ({len(raw_list)} items): {raw_list}")
    
    normalized = skill_normalizer.normalize_skills(raw_list)
    canonical_names = [name for name, _ in normalized]
    
    logger.info(f"  Normalized unique skills ({len(canonical_names)} items): {canonical_names}")
    assert canonical_names == ["Python", "FastAPI", "PostgreSQL"]


def test_job_normalizer_title():
    """Kiểm tra JobNormalizer làm sạch tiêu đề công việc."""
    logger.info("--- [TEST] Job Normalizer Title Cleaning ---")
    
    title_1 = "[HCM] Senior Python Developer (Urgent - Up to $3000)"
    cleaned_1 = job_normalizer.normalize_title(title_1)
    logger.info(f"  Raw: '{title_1}' -> Cleaned: '{cleaned_1}'")
    assert cleaned_1 == "Senior Python Developer"

    title_2 = "[HN] Tuyển gấp Tech Lead Golang | Lương hấp dẫn"
    cleaned_2 = job_normalizer.normalize_title(title_2)
    logger.info(f"  Raw: '{title_2}' -> Cleaned: '{cleaned_2}'")
    assert cleaned_2 == "Tech Lead Golang"


def test_job_normalizer_company():
    """Kiểm tra JobNormalizer loại bỏ hậu tố pháp nhân công ty."""
    logger.info("--- [TEST] Job Normalizer Company Cleaning ---")
    
    test_cases = [
        ("FPT Software Co., Ltd", "FPT Software"),
        ("Công ty Cổ phần VNG", "VNG"),
        ("Tiki Corporation Vietnam", "Tiki"),
    ]

    for raw, expected in test_cases:
        cleaned = job_normalizer.normalize_company(raw)
        logger.info(f"  Raw Company: '{raw}' -> Cleaned: '{cleaned}'")
        assert cleaned == expected


def test_job_normalizer_location_and_work_mode():
    """Kiểm tra chuẩn hóa địa điểm và suy luận hình thức làm việc."""
    logger.info("--- [TEST] Location & Work Mode Normalization ---")
    
    loc_1, mode_1 = job_normalizer.normalize_location("Quận 1, TP.HCM")
    logger.info(f"  'Quận 1, TP.HCM' -> City: '{loc_1}', Mode: '{mode_1.value}'")
    assert loc_1 == "Ho Chi Minh City"
    assert mode_1 == WorkModeEnum.ONSITE

    loc_2, mode_2 = job_normalizer.normalize_location("Cầu Giấy, Hà Nội (Hybrid)")
    logger.info(f"  'Cầu Giấy, Hà Nội (Hybrid)' -> City: '{loc_2}', Mode: '{mode_2.value}'")
    assert loc_2 == "Hanoi"
    assert mode_2 == WorkModeEnum.HYBRID

    loc_3, mode_3 = job_normalizer.normalize_location("Worldwide (100% Remote)")
    logger.info(f"  'Worldwide (100% Remote)' -> Mode: '{mode_3.value}'")
    assert mode_3 == WorkModeEnum.REMOTE


def test_job_normalizer_level():
    """Kiểm tra suy luận cấp bậc công việc từ title và description."""
    logger.info("--- [TEST] Job Level Inference ---")
    
    test_cases = [
        ("Internship Backend Engineer", JobLevelEnum.INTERN),
        ("Fresher Java Developer", JobLevelEnum.FRESHER),
        ("Junior React Developer", JobLevelEnum.JUNIOR),
        ("Senior DevOps Engineer", JobLevelEnum.SENIOR),
        ("Engineering Team Lead", JobLevelEnum.LEAD),
        ("Software Engineer", JobLevelEnum.UNKNOWN),
    ]

    for title, expected_level in test_cases:
        level = job_normalizer.normalize_level(title)
        logger.info(f"  Title: '{title}' -> Inferred Level: {level.value}")
        assert level == expected_level


def test_job_normalizer_salary():
    """Kiểm tra trích xuất và chuẩn hóa mức lương."""
    logger.info("--- [TEST] Salary Normalization ---")
    
    min_sal, max_sal, curr, is_neg = job_normalizer.normalize_salary(raw_text="$1,500 - $3,000")
    logger.info(f"  Raw: '$1,500 - $3,000' -> Min: {min_sal}, Max: {max_sal}, Currency: {curr}, Negotiable: {is_neg}")
    assert min_sal == 1500.0
    assert max_sal == 3000.0
    assert curr == "USD"
    assert is_neg is False

    min_sal_vnd, max_sal_vnd, curr_vnd, _ = job_normalizer.normalize_salary(raw_text="20 - 40 triệu VND")
    logger.info(f"  Raw: '20 - 40 triệu VND' -> Min: {min_sal_vnd:,.0f} {curr_vnd}, Max: {max_sal_vnd:,.0f} {curr_vnd}")
    assert min_sal_vnd == 20000000.0
    assert max_sal_vnd == 40000000.0
    assert curr_vnd == "VND"

    _, _, _, is_neg_true = job_normalizer.normalize_salary(raw_text="Lương thỏa thuận theo năng lực")
    logger.info(f"  Raw: 'Lương thỏa thuận theo năng lực' -> Negotiable: {is_neg_true}")
    assert is_neg_true is True
