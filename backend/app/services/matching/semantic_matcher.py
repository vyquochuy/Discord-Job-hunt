import math
from typing import List, Optional, Tuple
from app.services.matching.models import (
    CandidateProfileDTO,
    ConfidenceLevel,
    EvidenceItem,
    EvidenceStatus,
    JobMatchInputDTO,
    MatchSignal,
)


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """
    Tính Cosine Similarity chuẩn toán học giữa 2 vectors.
    Kết quả nằm trong đoạn [-1.0, 1.0].
    """
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)


def compute_fallback_project_relevance(
    candidate: CandidateProfileDTO, job: JobMatchInputDTO
) -> Tuple[float, ConfidenceLevel, str, List[EvidenceItem]]:
    """
    Thuật toán đối soát dự án phân tích chuyên sâu khi không có vector embeddings:
    1. Đánh giá độ phủ công nghệ giữa dự án và JD.
    2. Đánh giá tính liên quan miền (Domain Match): Web, Mobile, Cloud, Security, AI/ML.
    3. Đánh giá chiều sâu thực thi (Evidence Depth): Benchmarks, Load-testing, Architecture.
    """
    if not candidate.projects:
        return (
            0.5,
            ConfidenceLevel.INSUFFICIENT_EVIDENCE,
            "Hồ sơ chưa có thông tin dự án (cần trao đổi thêm về kinh nghiệm làm bài tập lớn)",
            [],
        )

    job_skills_set = set(s.lower() for s in job.all_skills)
    job_text = f"{job.title} {job.description} {job.requirements_summary or ''}".lower()

    # Nhận diện miền bài toán từ JD
    is_web_domain = any(k in job_text for k in ["web", "frontend", "fullstack", "react", "nextjs", "backend", "api"])
    is_mobile_domain = any(k in job_text for k in ["mobile", "flutter", "react native", "ios", "android", "dart"])
    is_cloud_devops = any(k in job_text for k in ["cloud", "devops", "sre", "docker", "kubernetes", "linux", "system"])
    is_general_software = any(k in job_text for k in ["software engineer", "software development", "lập trình", "phần mềm", "intern"])

    project_scores: List[float] = []
    evidences: List[EvidenceItem] = []

    for proj in candidate.projects:
        proj_tech_set = set(t.lower() for t in proj.technologies)
        proj_text = f"{proj.name} {proj.summary or ''} {' '.join(proj.technologies)}".lower()

        # 1. Tech Overlap
        tech_overlap_score = 0.0
        if job_skills_set:
            matched_tech = proj_tech_set.intersection(job_skills_set)
            tech_overlap_score = len(matched_tech) / len(job_skills_set)

        # 2. Domain Match
        domain_score = 0.5
        matched_domains = []
        if is_web_domain and any(w in proj_text for w in ["web", "react", "nextjs", "full-stack", "worker", "hono", "websocket"]):
            domain_score = max(domain_score, 0.9)
            matched_domains.append("Web/Fullstack")
        if is_mobile_domain and any(m in proj_text for m in ["flutter", "mobile", "dart", "android", "keystore"]):
            domain_score = max(domain_score, 0.9)
            matched_domains.append("Mobile")
        if is_cloud_devops and any(c in proj_text for c in ["cloudflare", "docker", "rate-limiting", "serverless", "linux", "d1", "kv"]):
            domain_score = max(domain_score, 0.85)
            matched_domains.append("Cloud/Infrastructure")
        if is_general_software and (len(proj.technologies) >= 3 or len(proj.evidence) >= 2):
            domain_score = max(domain_score, 0.85)
            matched_domains.append("Software Engineering")

        # 3. Execution Depth
        depth_score = 0.6
        if len(proj.evidence) >= 2 or (proj.summary and len(proj.summary) > 50):
            depth_score = 0.9

        # Composite project score
        if job_skills_set:
            final_p_score = (tech_overlap_score * 0.4) + (domain_score * 0.4) + (depth_score * 0.2)
        else:
            # JD không có tech skills cụ thể -> Domain Match + Depth quyết định
            final_p_score = (domain_score * 0.6) + (depth_score * 0.4)

        final_p_score = min(1.0, max(0.0, final_p_score))
        project_scores.append(final_p_score)

        if final_p_score >= 0.7:
            evidences.append(
                EvidenceItem(
                    source_type="PROJECT",
                    source_id=proj.name,
                    title=f"Dự án tiêu biểu: {proj.name}",
                    excerpt=f"{proj.summary or ''} [Điểm phù hợp: {(final_p_score * 100):.0f}%]",
                )
            )

    # Top-1 + Top-2 weighted average
    sorted_scores = sorted(project_scores, reverse=True)
    if len(sorted_scores) == 1:
        composite_score = sorted_scores[0]
    else:
        composite_score = (sorted_scores[0] * 0.7) + (sorted_scores[1] * 0.3)

    reason = f"Dự án tốt nhất đạt {(sorted_scores[0] * 100):.0f}% độ phù hợp domain/công nghệ với {len(evidences)} bằng chứng tiêu biểu"
    return round(composite_score, 4), ConfidenceLevel.HIGH, reason, evidences


def compute_project_relevance(
    candidate: CandidateProfileDTO,
    job: JobMatchInputDTO,
    project_embeddings: Optional[List[List[float]]] = None,
) -> Tuple[float, ConfidenceLevel, str, List[EvidenceItem]]:
    """
    Tính độ liên quan giữa các dự án của ứng viên và tin tuyển dụng:
    - Per-project cosine similarity -> max(top similarities) (Dự án phù hợp nhất quyết định điểm số).
    - Chuẩn hóa Cosine từ [-1.0, 1.0] về đoạn [0.0, 1.0]: normalized = (raw_cosine + 1.0) / 2.0.
    - Fallback về phân tích domain + evidence khi không có vector embeddings.
    """
    if not candidate.projects:
        return (
            0.5,
            ConfidenceLevel.INSUFFICIENT_EVIDENCE,
            "Chưa có dự án trong hồ sơ (INSUFFICIENT_EVIDENCE)",
            [],
        )

    # Nếu có vector embeddings cho cả job và từng dự án
    if job.embedding and project_embeddings and len(project_embeddings) == len(candidate.projects):
        similarities: List[float] = []
        evidences: List[EvidenceItem] = []

        for idx, proj_emb in enumerate(project_embeddings):
            if proj_emb:
                raw_cosine = cosine_similarity(proj_emb, job.embedding)
                # Normalize cosine ∈ [-1, 1] to [0, 1]
                normalized = max(0.0, min(1.0, (raw_cosine + 1.0) / 2.0))
                similarities.append(normalized)
                proj = candidate.projects[idx]
                if normalized >= 0.65:
                    evidences.append(
                        EvidenceItem(
                            source_type="PROJECT",
                            source_id=proj.name,
                            title=f"Dự án {proj.name}",
                            excerpt=f"{proj.summary or ''} [Vector similarity: {normalized:.2f}]",
                        )
                    )

        if similarities:
            sorted_sims = sorted(similarities, reverse=True)
            best_score = sorted_sims[0] if len(sorted_sims) == 1 else (sorted_sims[0] * 0.7 + sorted_sims[1] * 0.3)
            return (
                round(best_score, 4),
                ConfidenceLevel.HIGH,
                f"Độ tương đồng ngữ nghĩa vector đạt {(best_score * 100):.1f}%",
                evidences,
            )

    # Fallback domain + keyword matching
    return compute_fallback_project_relevance(candidate, job)
