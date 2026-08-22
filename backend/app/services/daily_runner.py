import asyncio
import logging
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.candidate import Candidate
from app.models.job import Job, JobStatusEnum
from app.models.match import JobMatch
from app.repositories.candidate import CandidateRepository
from app.services.candidate import CandidateService
from app.services.collectors.careerlink_adapter import CareerLinkJobCollector
from app.services.collectors.itviec_adapter import ITViecJobCollector
from app.services.collectors.remotive_adapter import RemotiveJobCollector
from app.services.collectors.topcv_adapter import TopCVJobCollector
from app.services.ingestion_pipeline import ingestion_pipeline, IngestionStats
from app.services.matching.match_service import job_match_service
from app.services.matching.models import Eligibility, RecommendationCategory
from app.services.normalization.skill_normalizer import skill_normalizer

logger = logging.getLogger("daily_runner")


class TopRecommendedJobSummary(BaseModel):
    job_id: str
    title: str
    company: str
    location: Optional[str] = None
    score: float
    recommendation: str
    eligibility: str
    matched_skills: List[str] = []
    missing_required_skills: List[str] = []
    contact_email: Optional[str] = None
    apply_url: Optional[str] = None


class DailyBatchSummary(BaseModel):
    started_at: datetime
    finished_at: datetime
    duration_seconds: float
    candidate_name: str
    candidate_id: str

    # Ingestion Stats
    sources_scanned: List[str] = []
    total_fetched: int = 0
    new_jobs_created: int = 0
    unchanged_jobs: int = 0
    duplicates_detected: int = 0
    ingestion_errors: int = 0

    # Matching Stats
    total_active_jobs: int = 0
    total_matches_evaluated: int = 0
    strong_matches_count: int = 0
    good_matches_count: int = 0
    review_required_count: int = 0
    blocked_count: int = 0

    # Top recommendations
    top_recommendations: List[TopRecommendedJobSummary] = []
    status: str = "COMPLETED"
    error_message: Optional[str] = None


class DailyBatchRunnerService:
    """
    Dịch vụ điều phối chu kỳ chạy Batch hàng ngày (1 lần / ngày):
    1. Đồng bộ Candidate Profile từ context/ (candidate-profile.yaml, master-resume.tex).
    2. Đồng bộ Canonical Skill Taxonomy.
    3. Cào tin mới từ các Collectors với chi phí 0đ (Zero-LLM Cost Ingestion).
    4. Chạy Hard Filter & Scoring Engine (Phase 3 Job Intelligence).
    5. Trích xuất Top Jobs có điểm phù hợp cao nhất.
    6. Tạo báo cáo Daily Report chi tiết.
    """

    @classmethod
    async def run_daily_batch(
        cls,
        session: Optional[AsyncSession] = None,
        limit_per_source: int = 15,
        context_dir: Optional[str] = None,
    ) -> DailyBatchSummary:
        if session is not None:
            return await cls._execute_batch(session, limit_per_source, context_dir)
        else:
            async with AsyncSessionLocal() as sess:
                return await cls._execute_batch(sess, limit_per_source, context_dir)

    @classmethod
    async def _execute_batch(
        cls,
        session: AsyncSession,
        limit_per_source: int = 15,
        context_dir: Optional[str] = None,
    ) -> DailyBatchSummary:
        start_time = datetime.now(timezone.utc)
        t0 = time.time()
        logger.info("==================================================")
        logger.info(f"🚀 Starting Daily Batch Autonomous Job Run at {start_time.isoformat()}...")
        logger.info("==================================================")

        sources_scanned = []
        total_fetched = 0
        new_jobs_created = 0
        unchanged_jobs = 0
        duplicates_detected = 0
        ingestion_errors = 0

        # 1. Đồng bộ Candidate Profile từ context/
        logger.info("Step 1/5: Syncing Candidate Profile & Master Resume context...")
        try:
            await CandidateService.sync_profile_from_context(session, context_dir=context_dir)
            candidate = await CandidateRepository.get_profile(session)
            if not candidate:
                raise ValueError("Candidate profile not found after sync.")
            logger.info(f"✅ Candidate profile synced: {candidate.full_name} ({candidate.headline})")
        except Exception as e:
            logger.error(f"❌ Failed to sync candidate profile: {e}", exc_info=True)
            raise RuntimeError(f"Candidate profile sync failed: {e}")

        # 2. Đồng bộ Skill Taxonomy
        logger.info("Step 2/5: Seeding and synchronizing Canonical Skill Taxonomy...")
        try:
            await skill_normalizer.seed_or_sync_db(session)
            logger.info("✅ Canonical Skill Taxonomy verified and synced.")
        except Exception as e:
            logger.warning(f"⚠️ Non-blocking warning during skill taxonomy sync: {e}")

        # 3. Thu thập Job mới từ các Collectors (Zero LLM cost)
        logger.info("Step 3/5: Collecting new jobs from active sources (Zero LLM Cost)...")
        collectors = [
            RemotiveJobCollector(),
            ITViecJobCollector(),
            CareerLinkJobCollector(),
            TopCVJobCollector(),
        ]

        for col in collectors:
            sources_scanned.append(col.source_name)
            try:
                stats: IngestionStats = await ingestion_pipeline.run(
                    collector=col,
                    db=session,
                    limit=limit_per_source,
                    use_llm=False,  # BẢO ĐẢM CHI PHÍ 0Đ
                )
                total_fetched += stats.total_fetched
                new_jobs_created += stats.created
                unchanged_jobs += stats.unchanged
                duplicates_detected += stats.duplicates_detected
                ingestion_errors += stats.errors
            except Exception as e:
                logger.error(f"❌ Error during collection for source {col.source_name}: {e}", exc_info=True)
                ingestion_errors += 1

        # 4. Phân tích & Chấm điểm phù hợp hàng loạt (Phase 3 Match Engine)
        logger.info("Step 4/5: Running Job Intelligence & Deterministic Scoring on all active jobs...")
        matches_evaluated = await job_match_service.batch_calculate_all(session, candidate_id=candidate.id)
        logger.info(f"✅ Evaluated {matches_evaluated} active jobs against candidate profile.")

        # 5. Thống kê & Trích xuất Top Recommendations
        logger.info("Step 5/5: Aggregating statistics and extracting top job recommendations...")

        # Đếm tổng active jobs
        stmt_active = select(func.count(Job.id)).where(Job.status == JobStatusEnum.ACTIVE)
        res_active = await session.execute(stmt_active)
        total_active = res_active.scalar() or 0

        # Đếm phân loại khuyến nghị
        stmt_matches = select(JobMatch).where(JobMatch.candidate_id == candidate.id)
        res_matches = await session.execute(stmt_matches)
        all_matches = res_matches.scalars().all()

        strong_count = sum(1 for m in all_matches if m.recommendation == RecommendationCategory.STRONG_MATCH)
        good_count = sum(1 for m in all_matches if m.recommendation == RecommendationCategory.GOOD_MATCH)
        review_count = sum(1 for m in all_matches if m.recommendation == RecommendationCategory.REVIEW_REQUIRED)
        blocked_count = sum(1 for m in all_matches if m.eligibility == Eligibility.BLOCKED)

        # Lấy Top 10 recommendations điểm cao nhất (score >= 60.0 và không bị BLOCKED)
        top_recs_db = await job_match_service.get_top_recommendations(
            session, candidate_id=candidate.id, limit=10, min_score=60.0
        )

        top_recs_summary: List[TopRecommendedJobSummary] = []
        for rec in top_recs_db:
            top_recs_summary.append(
                TopRecommendedJobSummary(
                    job_id=str(rec.job.id),
                    title=rec.job.title,
                    company=rec.job.company_name,
                    location=rec.job.location,
                    score=rec.score,
                    recommendation=rec.recommendation.value,
                    eligibility=rec.eligibility.value,
                    matched_skills=rec.matched_skills or [],
                    missing_required_skills=rec.missing_required_skills or [],
                    contact_email=rec.job.contact_email,
                    apply_url=rec.job.apply_url or (rec.job.raw_job.source_url if rec.job.raw_job else None),
                )
            )

        end_time = datetime.now(timezone.utc)
        duration = round(time.time() - t0, 2)

        summary = DailyBatchSummary(
            started_at=start_time,
            finished_at=end_time,
            duration_seconds=duration,
            candidate_name=candidate.full_name,
            candidate_id=str(candidate.id),
            sources_scanned=sources_scanned,
            total_fetched=total_fetched,
            new_jobs_created=new_jobs_created,
            unchanged_jobs=unchanged_jobs,
            duplicates_detected=duplicates_detected,
            ingestion_errors=ingestion_errors,
            total_active_jobs=total_active,
            total_matches_evaluated=matches_evaluated,
            strong_matches_count=strong_count,
            good_matches_count=good_count,
            review_required_count=review_count,
            blocked_count=blocked_count,
            top_recommendations=top_recs_summary,
            status="COMPLETED",
        )

        logger.info("==================================================")
        logger.info(f"🏁 Daily Batch Completed in {duration}s!")
        logger.info(f"📊 Fetched: {total_fetched} | New: {new_jobs_created} | Unchanged: {unchanged_jobs} | Duplicates: {duplicates_detected}")
        logger.info(f"🎯 Evaluated Matches: {matches_evaluated} (🌟 Strong: {strong_count}, ✅ Good: {good_count}, ⚠️ Review: {review_count}, ⛔ Blocked: {blocked_count})")
        logger.info(f"🏆 Top High-Scoring Jobs: {len(top_recs_summary)}")
        logger.info("==================================================")

        return summary


daily_batch_runner = DailyBatchRunnerService()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    asyncio.run(daily_batch_runner.run_daily_batch(limit_per_source=10))
