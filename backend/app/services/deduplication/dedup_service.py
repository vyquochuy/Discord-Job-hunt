import logging
from typing import List, Optional, Tuple
from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.job import Job, JobStatusEnum
from app.services.normalization.job_normalizer import job_normalizer

logger = logging.getLogger("dedup_service")


class DeduplicationResult:
    def __init__(
        self,
        is_duplicate: bool,
        duplicate_job_id: Optional[str] = None,
        strategy: Optional[str] = None,  # "EXACT" | "FUZZY" | "SEMANTIC"
        confidence_score: float = 0.0,
        reason: Optional[str] = None,
    ):
        self.is_duplicate = is_duplicate
        self.duplicate_job_id = duplicate_job_id
        self.strategy = strategy
        self.confidence_score = confidence_score
        self.reason = reason


class DeduplicationService:
    """
    Engine khử trùng lặp tin tuyển dụng 3 tầng:
    1. Exact Match: So khớp chữ ký hash (normalized_company:normalized_title:location)
    2. Fuzzy Match: RapidFuzz so khớp độ tương đồng tên công ty & tiêu đề công việc
    3. Semantic Match: So khớp vector embedding Cosine similarity (khi ở vùng phân vân)
    """

    # Ngưỡng tương đồng
    FUZZY_COMPANY_THRESHOLD = 85.0
    FUZZY_TITLE_THRESHOLD = 85.0
    SEMANTIC_SIMILARITY_THRESHOLD = 0.90

    async def check_duplicate(
        self,
        db: AsyncSession,
        dedup_signature: str,
        normalized_company: str,
        normalized_title: str,
        normalized_location: Optional[str] = None,
        job_level: Optional[str] = None,
        embedding: Optional[List[float]] = None,
    ) -> DeduplicationResult:
        """
        Kiểm tra một Job có bị trùng lặp với các Job đang ACTIVE trong database hay không.
        """
        # =========================================================================
        # TẦNG 1: EXACT SIGNATURE MATCH
        # =========================================================================
        if dedup_signature:
            stmt_exact = select(Job).where(
                Job.dedup_signature == dedup_signature,
                Job.status == JobStatusEnum.ACTIVE,
            )
            res_exact = await db.execute(stmt_exact)
            exact_match = res_exact.scalars().first()

            if exact_match:
                logger.info(f"[Dedup Tier 1 - EXACT] Trùng lặp chính xác với Job ID {exact_match.id}")
                return DeduplicationResult(
                    is_duplicate=True,
                    duplicate_job_id=str(exact_match.id),
                    strategy="EXACT",
                    confidence_score=1.0,
                    reason="Trùng khớp hoàn toàn chữ ký (Company, Title, Location)",
                )

        # =========================================================================
        # TẦNG 2: FUZZY STRING MATCHING (RapidFuzz)
        # =========================================================================
        # Lấy danh sách các jobs đang ACTIVE để so sánh
        stmt_active = select(Job).where(Job.status == JobStatusEnum.ACTIVE).limit(200)
        res_active = await db.execute(stmt_active)
        active_jobs = res_active.scalars().all()

        for existing_job in active_jobs:
            comp_a = job_normalizer.normalize_company(normalized_company).lower()
            comp_b = job_normalizer.normalize_company(existing_job.normalized_company).lower()
            
            company_score = (
                100.0 if comp_a == comp_b and comp_a
                else fuzz.token_set_ratio(comp_a, comp_b)
            )
            title_score = fuzz.token_sort_ratio(
                normalized_title.lower(), existing_job.normalized_title.lower()
            )

            # Trường hợp 2: Khớp mạnh cả công ty và title
            if (
                company_score >= self.FUZZY_COMPANY_THRESHOLD
                and title_score >= self.FUZZY_TITLE_THRESHOLD
            ):
                # Nếu khác cấp bậc rõ ràng (VD Junior vs Senior) thì không tính là duplicate
                if (
                    job_level
                    and existing_job.level.value != "UNKNOWN"
                    and job_level != "UNKNOWN"
                    and job_level != existing_job.level.value
                ):
                    continue

                avg_score = (company_score + title_score) / 200.0
                logger.info(
                    f"[Dedup Tier 2 - FUZZY] Trùng lặp tương đồng cao ({avg_score:.2f}) với Job {existing_job.id}"
                )
                return DeduplicationResult(
                    is_duplicate=True,
                    duplicate_job_id=str(existing_job.id),
                    strategy="FUZZY",
                    confidence_score=avg_score,
                    reason=f"Fuzzy Match: Company ({company_score:.0f}%), Title ({title_score:.0f}%)",
                )

        # =========================================================================
        # TẦNG 3: SEMANTIC EMBEDDINGS (pgvector / Cosine Distance)
        # =========================================================================
        # Chỉ chạy khi có vector embedding và có các jobs tiềm năng trong DB
        if embedding and len(embedding) > 0:
            # Nếu chạy trên PostgreSQL với pgvector, có thể dùng Job.embedding.cosine_distance(embedding)
            # Ở mức abstraction an toàn cho cả test SQLite, ta kiểm tra nếu cột embedding có giá trị
            for existing_job in active_jobs:
                if existing_job.embedding is not None and isinstance(existing_job.embedding, (list, tuple)):
                    cos_sim = self._calculate_cosine_similarity(embedding, existing_job.embedding)
                    if cos_sim >= self.SEMANTIC_SIMILARITY_THRESHOLD:
                        logger.info(
                            f"[Dedup Tier 3 - SEMANTIC] Trùng lặp ngữ nghĩa ({cos_sim:.2f}) với Job {existing_job.id}"
                        )
                        return DeduplicationResult(
                            is_duplicate=True,
                            duplicate_job_id=str(existing_job.id),
                            strategy="SEMANTIC",
                            confidence_score=cos_sim,
                            reason=f"Semantic Cosine Similarity ({cos_sim * 100:.1f}%)",
                        )

        return DeduplicationResult(is_duplicate=False)

    @staticmethod
    def _calculate_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Tính Cosine Similarity giữa 2 vector."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm_a = sum(a * a for a in vec1) ** 0.5
        norm_b = sum(b * b for b in vec2) ** 0.5
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot_product / (norm_a * norm_b)


# Singleton Instance
dedup_service = DeduplicationService()
