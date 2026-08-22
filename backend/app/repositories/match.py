import uuid
from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.job import Job
from app.models.match import JobMatch
from app.services.matching.models import Eligibility, RecommendationCategory


class MatchRepository:
    """
    Repository quản lý truy vấn và lưu trữ kết quả phân tích mức độ phù hợp (JobMatch).
    """

    @staticmethod
    async def get_match_by_job_id(
        session: AsyncSession, candidate_id: uuid.UUID, job_id: uuid.UUID
    ) -> Optional[JobMatch]:
        """Lấy kết quả match theo candidate_id và job_id."""
        stmt = (
            select(JobMatch)
            .options(
                selectinload(JobMatch.job).selectinload(Job.raw_job),
                selectinload(JobMatch.candidate),
            )
            .where(JobMatch.candidate_id == candidate_id, JobMatch.job_id == job_id)
        )
        result = await session.execute(stmt)
        return result.scalars().first()


    @classmethod
    async def upsert_match(
        cls, session: AsyncSession, match_data: JobMatch
    ) -> JobMatch:
        """
        Lưu hoặc cập nhật kết quả phân tích match.
        Nếu đã tồn tại bản ghi cho (candidate_id, job_id), cập nhật dữ liệu mới nhất.
        """
        existing = await cls.get_match_by_job_id(
            session, match_data.candidate_id, match_data.job_id
        )

        if existing:
            existing.score = match_data.score
            existing.eligibility = match_data.eligibility
            existing.eligibility_reasons = match_data.eligibility_reasons
            existing.recommendation = match_data.recommendation
            existing.is_passed_hard_filters = match_data.is_passed_hard_filters
            existing.hard_filter_results = match_data.hard_filter_results
            existing.matched_skills = match_data.matched_skills
            existing.missing_required_skills = match_data.missing_required_skills
            existing.missing_preferred_skills = match_data.missing_preferred_skills
            existing.signals = match_data.signals
            existing.warnings = match_data.warnings
            existing.explanation = match_data.explanation
            existing.raw_explanation_payload = match_data.raw_explanation_payload
            existing.scoring_version = match_data.scoring_version
            existing.taxonomy_version = match_data.taxonomy_version
            existing.candidate_snapshot = match_data.candidate_snapshot
            existing.job_snapshot = match_data.job_snapshot
            target = existing
        else:
            session.add(match_data)
            target = match_data

        await session.commit()
        await session.refresh(target)
        return target

    @staticmethod
    async def list_matches(
        session: AsyncSession,
        candidate_id: uuid.UUID,
        min_score: Optional[float] = None,
        eligibility: Optional[Eligibility] = None,
        recommendation: Optional[RecommendationCategory] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[JobMatch], int]:
        """Lấy danh sách phân tích match có phân trang và bộ lọc."""
        query = select(JobMatch).where(JobMatch.candidate_id == candidate_id)

        if min_score is not None:
            query = query.where(JobMatch.score >= min_score)
        if eligibility:
            query = query.where(JobMatch.eligibility == eligibility)
        if recommendation:
            query = query.where(JobMatch.recommendation == recommendation)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_res = await session.execute(count_query)
        total = total_res.scalar() or 0

        # Pagination and order
        offset = (page - 1) * page_size
        query = (
            query.options(selectinload(JobMatch.job).selectinload(Job.raw_job))
            .order_by(JobMatch.score.desc(), JobMatch.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )

        result = await session.execute(query)
        items = result.scalars().all()
        return list(items), total

    @staticmethod
    async def get_top_recommendations(
        session: AsyncSession,
        candidate_id: uuid.UUID,
        limit: int = 10,
        min_score: float = 60.0,
    ) -> List[JobMatch]:
        """Lấy top công việc được khuyến nghị nhất cho ứng viên (không bị BLOCKED, điểm >= min_score)."""
        stmt = (
            select(JobMatch)
            .options(selectinload(JobMatch.job).selectinload(Job.raw_job))
            .where(
                JobMatch.candidate_id == candidate_id,
                JobMatch.eligibility != Eligibility.BLOCKED,
                JobMatch.score >= min_score,
            )
            .order_by(JobMatch.score.desc(), JobMatch.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())



match_repository = MatchRepository()
