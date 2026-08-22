import logging
import pytest
from app.models.job import JobLevelEnum, WorkModeEnum
from app.services.matching.models import (
    CandidateEducationDTO,
    CandidateProfileDTO,
    CandidateProjectDTO,
    ConfidenceLevel,
    Eligibility,
    EvidenceStatus,
    JobMatchInputDTO,
    RecommendationCategory,
)
from app.services.matching.scoring_engine import calculate_match_score

logger = logging.getLogger("test_golden_intern_job")


def test_golden_software_engineer_intern_jd_matching():
    """
    Regression & Golden Test Case:
    Kiểm tra toàn diện JD Software Engineer Intern (8c7b642e-d122-4bf9-8522-7334379b5198):
    - JD không có danh sách từ khóa kỹ thuật cứng -> Không được phạt 0% technical_skill_match và không được áp Score Cap <= 50.
    - JD không yêu cầu kinh nghiệm -> experience_relevance = 1.0 (NOT_REQUIRED).
    - JD yêu cầu tư duy logic, Web/Mobile, Test-First, AI utilization -> requirement_fit >= 0.8 (SUPPORTED).
    - Dự án VYVYCHAT (Web) & Account Manager (Mobile) -> project_relevance >= 0.8 (SUPPORTED).
    - Vị trí thực tập sinh tương thích -> seniority_match = 1.0.
    - Học vấn ĐH Khoa học Tự nhiên ngành KHMT -> education_match = 1.0.
    - Địa điểm Thủ Đức, TP.HCM -> work_fit >= 0.85.
    - Tổng điểm đạt xuất sắc >= 80/100, Eligibility = ELIGIBLE.
    """
    logger.info("=== [TEST] Golden Test Case: Software Engineer Intern Evidence Matching ===")

    # 1. Ứng viên thực tế từ context/candidate-profile.yaml
    candidate = CandidateProfileDTO(
        full_name="Vy Quoc Huy",
        headline="System Intern",
        location="Thu Duc, Ho Chi Minh",
        summary="Final-year Computer Science student with interest in Linux systems, cloud infrastructure, and distributed software systems.",
        target_roles=["System Intern", "DevOps Engineer Intern", "Backend Developer"],
        target_locations=["Ho Chi Minh City", "Remote", "Hybrid"],
        skills=["Python", "JavaScript", "TypeScript", "C++", "Dart", "React", "NextJS", "FastAPI", "PostgreSQL", "Docker", "Linux"],
        soft_skills=["Problem-solving", "System design thinking", "Technical documentation", "Teamwork"],
        education=[
            CandidateEducationDTO(
                institution="VNUHCM - University of Science",
                degree="Bachelor",
                field="Computer Science - Cyber Security",
                graduation_year=2026,
                gpa="3.15/4.0",
                coursework=[
                    "Computer Networks",
                    "Database Systems",
                    "Fundamentals of Artificial Intelligence",
                    "Introduction to Machine Learning",
                    "Introduction to Cryptography",
                    "Data Structures",
                ],
            )
        ],
        projects=[
            CandidateProjectDTO(
                name="VYVYCHAT",
                role="Full-stack Developer",
                summary="Full-stack real-time messaging web platform built on Cloudflare's serverless infrastructure with WebSocket Durable Objects",
                technologies=["React", "TypeScript", "Tailwind CSS", "Cloudflare Workers", "Durable Objects", "Cloudflare D1"],
                evidence=[
                    {
                        "title": "Cryptography & E2EE",
                        "detail": "Architected zero-knowledge End-to-End Encryption with secure ECDH P-256 key exchange; verified correct decryption across 3 device sessions.",
                    },
                    {
                        "title": "Stateful Real-Time Edge",
                        "detail": "Engineered stateful WebSocket layer using Cloudflare Durable Objects, achieving measured round-trip latency of ~45ms under concurrent load.",
                    },
                    {
                        "title": "Serverless Infrastructure & Rate-Limiting",
                        "detail": "Designed relational data model on Cloudflare D1 (SQLite) and token-bucket rate-limiting; load-tested to sustain 200 req/min blocking brute-force.",
                    },
                ],
            ),
            CandidateProjectDTO(
                name="Account Manager: Zero-Knowledge Password Vault",
                role="Author & Lead Developer",
                summary="Flutter mobile application for securely managing credentials offline with a Zero-Knowledge backend sync model",
                technologies=["Cloudflare Workers", "Hono", "TypeScript", "Flutter", "Dart", "Android Keystore/Keychain", "Argon2id"],
                evidence=[
                    {
                        "title": "Serverless API & Sync Architecture",
                        "detail": "Designed scalable serverless sync backend using Hono framework (TypeScript); API benchmarked at < 80ms average response time.",
                    },
                    {
                        "title": "Relational Database Schema",
                        "detail": "Modeled 9-table relational database schema in Cloudflare D1 (SQLite) supporting multi-tenant metadata and Shamir Secret Sharing.",
                    },
                ],
            ),
        ],
        experiences=[],  # Chưa có kinh nghiệm công ty chính thức
        preferences={
            "employment_types": ["Internship", "Full-time"],
            "remote": "hybrid",
            "minimum_salary": None,
        },
    )

    # 2. Golden JD (ID: 8c7b642e-d122-4bf9-8522-7334379b5198)
    golden_job = JobMatchInputDTO(
        title="Software Engineer Intern",
        company_name="Alliance Software Inc",
        location="Long Bình, Thủ Đức, TP.HCM",
        normalized_location="Ho Chi Minh City",
        work_mode=WorkModeEnum.ONSITE,
        level=JobLevelEnum.INTERN,
        is_salary_negotiable=True,
        required_skills=[],   # Không có explicit keyword tags
        preferred_skills=[],
        description="""
        Vị trí: Software Engineer Intern
        Yêu cầu:
        - Không yêu cầu kinh nghiệm chuyên môn.
        - Trình độ Đại học trở lên, ưu tiên sinh viên sắp tốt nghiệp chuyên ngành CNTT / Khoa học máy tính.
        - Không tuyển Fresher/Junior, chỉ tuyển Intern.
        - Đề cao tư duy logic, hiểu vấn đề, phản biện, chứng minh tính đúng đắn và Test First.
        - Hiểu AI và biết tận dụng AI trong phát triển phần mềm. Vibe Coding là một lợi thế.
        - Có kiến thức nền tảng ít nhất một lĩnh vực phát triển phần mềm như Web hoặc Mobile.
        - Kỹ năng giao tiếp, tinh thần chủ động và làm việc nhóm tốt.
        - Thời gian làm việc: 07:00 - 16:00 từ thứ Hai đến thứ Sáu.
        - Địa điểm: Long Bình, TP. Thủ Đức, TP. Hồ Chí Minh.
        """,
    )

    # 3. Chạy Matching Engine
    result = calculate_match_score(candidate=candidate, job=golden_job)

    # In chi tiết log
    logger.info(f"Final Score: {result.score:.2f}/100")
    logger.info(f"Eligibility: {result.eligibility.value}")
    logger.info(f"Recommendation: {result.recommendation.value}")
    for s in result.signals:
        logger.info(f"  Signal {s.name:25s}: Score={(s.score*100):.1f}% | Status={s.evidence_status.value:20s} | Weight={s.weight:.2f}")

    # 4. Kiểm tra các điều kiện (Assertions)
    # A. Eligibility
    assert result.eligibility == Eligibility.ELIGIBLE, f"Expected ELIGIBLE, got {result.eligibility}"

    # B. Signals Breakdown
    signals_dict = {s.name: s for s in result.signals}

    # B.1. Experience: Phải là NOT_REQUIRED (1.0) vì JD không yêu cầu kinh nghiệm
    exp_signal = signals_dict["experience_relevance"]
    assert exp_signal.evidence_status == EvidenceStatus.NOT_REQUIRED, f"Expected NOT_REQUIRED, got {exp_signal.evidence_status}"
    assert exp_signal.score == 1.0, f"Expected 1.0 for no experience required job, got {exp_signal.score}"

    # B.2. Technical Skills: Phải là NOT_REQUIRED (1.0) vì JD không yêu cầu explicit tech tags
    tech_signal = signals_dict["technical_skill_match"]
    assert tech_signal.evidence_status == EvidenceStatus.NOT_REQUIRED, f"Expected NOT_REQUIRED, got {tech_signal.evidence_status}"
    assert tech_signal.score == 1.0, f"Expected 1.0 when tech skills not required, got {tech_signal.score}"

    # B.3. Requirement Fit: Phải tìm thấy Evidence về Tư duy logic, Web/Mobile, AI Coursework
    req_signal = signals_dict["requirement_fit"]
    assert req_signal.evidence_status == EvidenceStatus.SUPPORTED, f"Expected SUPPORTED, got {req_signal.evidence_status}"
    assert req_signal.score >= 0.8, f"Expected >= 0.8 requirement fit, got {req_signal.score}"
    assert len(req_signal.evidence) >= 2, "Expected at least 2 evidence items"

    # B.4. Project Relevance: Dự án Web (VYVYCHAT) & Mobile (Account Manager)
    proj_signal = signals_dict["project_relevance"]
    assert proj_signal.evidence_status == EvidenceStatus.SUPPORTED, f"Expected SUPPORTED, got {proj_signal.evidence_status}"
    assert proj_signal.score >= 0.8, f"Expected >= 0.8 project relevance, got {proj_signal.score}"

    # B.5. Seniority Match: Intern ↔ Intern
    sen_signal = signals_dict["seniority_match"]
    assert sen_signal.score == 1.0, f"Expected 1.0 seniority match, got {sen_signal.score}"

    # B.6. Education Match: ĐH KHTN CS
    edu_signal = signals_dict["education_match"]
    assert edu_signal.score == 1.0, f"Expected 1.0 education match, got {edu_signal.score}"

    # B.7. Work Fit: Thu Duc / HCMC
    work_signal = signals_dict["work_fit"]
    assert work_signal.score >= 0.85, f"Expected >= 0.85 work fit, got {work_signal.score}"

    # C. Score & Recommendation
    assert result.score >= 80.0, f"Expected score >= 80.0 for golden match, got {result.score}"
    assert result.recommendation in (RecommendationCategory.STRONG_MATCH, RecommendationCategory.GOOD_MATCH)
    assert len(result.warnings) == 0, f"Expected no score cap warnings, got {result.warnings}"


def test_experience_required_vs_unsupported_candidate():
    """Kiểm tra: Nếu JD yêu cầu 2 năm kinh nghiệm nhưng ứng viên 0 năm -> MISMATCH (score thấp)."""
    candidate = CandidateProfileDTO(
        full_name="Vy Quoc Huy",
        headline="System Intern",
        experiences=[],
    )
    job = JobMatchInputDTO(
        title="Senior Python Engineer",
        company_name="Tech Corp",
        description="Yêu cầu tối thiểu 2 năm kinh nghiệm phát triển backend.",
        level=JobLevelEnum.MID,
    )
    res = calculate_match_score(candidate, job)
    exp_sig = next(s for s in res.signals if s.name == "experience_relevance")
    assert exp_sig.evidence_status == EvidenceStatus.MISMATCH
    assert exp_sig.score == 0.2


def test_strict_intern_exclusion_policy():
    """Kiểm tra: JD chỉ tuyển Intern (loại Fresher/Junior) -> Fresher bị FAIL."""
    fresher_candidate = CandidateProfileDTO(
        full_name="Fresher Dev",
        headline="Fresher Java Developer",
        target_roles=["Fresher Developer", "Junior Backend"],
    )
    job = JobMatchInputDTO(
        title="Software Engineer Intern",
        company_name="Strict Corp",
        description="Không tuyển Fresher/Junior, chỉ tuyển Intern.",
        level=JobLevelEnum.INTERN,
    )
    res = calculate_match_score(fresher_candidate, job)
    sen_filter = next(f for f in res.hard_filter_results if f.filter == "seniority")
    assert sen_filter.status.value == "FAIL"
    assert res.eligibility == Eligibility.BLOCKED
    assert res.recommendation == RecommendationCategory.DO_NOT_APPLY


@pytest.mark.asyncio
async def test_explanation_generation_with_evidence():
    """Kiểm tra việc sinh giải thích (Explanation) chứa đầy đủ bằng chứng đối soát."""
    from app.services.matching.explanation_service import explanation_service
    
    candidate = CandidateProfileDTO(
        full_name="Vy Quoc Huy",
        headline="System Intern",
        skills=["Python", "FastAPI"],
    )
    job = JobMatchInputDTO(
        title="Software Engineer Intern",
        company_name="Alliance",
        level=JobLevelEnum.INTERN,
    )
    score_res = calculate_match_score(candidate, job)
    
    explanation_text, raw_payload = await explanation_service.generate_explanation(
        candidate, job, score_res
    )
    
    assert explanation_text is not None
    assert len(explanation_text) > 20
    assert raw_payload is not None
    assert raw_payload["input_hash"] is not None

