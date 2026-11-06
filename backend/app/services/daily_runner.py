import asyncio
import logging
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.job import Job, JobStatusEnum
from app.models.match import JobMatch
from app.repositories.candidate import CandidateRepository
from app.services.candidate import CandidateService
from app.services.collectors.careerlink_adapter import CareerLinkJobCollector
from app.services.collectors.growupwork_adapter import GrowUpWorkJobCollector
from app.services.collectors.itnavi_adapter import ITNaviJobCollector
from app.services.collectors.itviec_adapter import ITViecJobCollector
from app.services.collectors.remotive_adapter import RemotiveJobCollector
from app.services.collectors.topcv_adapter import TopCVJobCollector
from app.services.collectors.topdev_adapter import TopDevJobCollector
from app.services.collectors.upwork_adapter import UpworkJobCollector
from app.services.collectors.vietnamworks_adapter import VietnamWorksJobCollector
from app.services.ingestion_pipeline import ingestion_pipeline, IngestionStats
from app.services.matching.match_service import job_match_service
from app.services.matching.models import Eligibility, RecommendationCategory
from app.services.normalization.skill_normalizer import skill_normalizer


logger = logging.getLogger("daily_runner")


# Phase 2.8: Các nền tảng Việt Nam được quét TOÀN BỘ job còn hiệu lực
# (không giới hạn limit) vì đây là nguồn chính cho thị trường mục tiêu.
FULL_SCAN_SOURCES = frozenset({"itviec", "topcv", "topdev", "vietnamworks", "careerlink"})

# Nguồn nước ngoài (remote quốc tế) chưa hỗ trợ quét toàn bộ -> giới hạn an toàn
FOREIGN_SOURCE_FULL_SCAN_CAP = 50


# Cấu hình các chế độ quét (Scan Modes) dùng chung cho API + Frontend.
# limit == 0 nghĩa là quét toàn bộ job còn hiệu lực mà nguồn có.
SCAN_MODE_CONFIG: dict = {
    "quick": {
        "label": "Quick Scan",
        "description": "Quét nhanh tin mới trong 24-48h qua (20 tin/nguồn, incremental).",
        "limit": 20,
        "full_scan": False,
    },
    "standard": {
        "label": "Standard Scan",
        "description": "Quét mở rộng 1-2 tuần qua (80 tin/nguồn, incremental).",
        "limit": 80,
        "full_scan": False,
    },
    "full": {
        "label": "Full Market Scan",
        "description": "Quét TOÀN BỘ tin còn hạn trên 5 nền tảng Việt Nam (không giới hạn).",
        "limit": 0,
        "full_scan": True,
    },
    "custom": {
        "label": "Custom Scan",
        "description": "Tự chọn số tin tối đa mỗi nguồn (1-500).",
        "limit": None,
        "full_scan": False,
    },
}


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

    # Scan configuration
    scan_mode: str = "standard"
    full_scan_sources: List[str] = []

    # Ingestion Stats
    sources_scanned: List[str] = []
    total_fetched: int = 0
    new_jobs_created: int = 0
    unchanged_jobs: int = 0
    duplicates_detected: int = 0
    ingestion_errors: int = 0
    expired_marked: int = 0
    expired_total: int = 0

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
        limit_per_source: int = 50,
        context_dir: Optional[str] = None,
        candidate_id: Optional[uuid.UUID] = None,
        scan_mode: Optional[str] = None,
    ) -> DailyBatchSummary:
        if session is not None:
            return await cls._execute_batch(
                session, limit_per_source, context_dir, candidate_id=candidate_id, scan_mode=scan_mode
            )
        else:
            async with AsyncSessionLocal() as sess:
                return await cls._execute_batch(
                    sess, limit_per_source, context_dir, candidate_id=candidate_id, scan_mode=scan_mode
                )

    @staticmethod
    def resolve_scan_plan(
        scan_mode: Optional[str],
        limit_per_source: int = 50,
    ) -> dict:
        """
        Quy đổi `scan_mode` thành kế hoạch quét cụ thể.

        Trả về: {"mode": str, "full_scan": bool, "per_source": {source: (limit, full_scan)}}
        - limit == 0 nghĩa là quét toàn bộ job còn hiệu lực.
        - Chế độ `full`: 5 nền tảng Việt Nam quét toàn bộ, nguồn ngoại giới hạn an toàn.
        - Không truyền `scan_mode` (legacy): giữ nguyên hành vi cũ (VN full scan, ngoại incremental).
        """
        normalized = (scan_mode or "").strip().lower()
        per_source: dict = {}

        if not normalized or normalized not in SCAN_MODE_CONFIG:
            # Legacy behavior: VN sources full scan + foreign incremental
            for src in FULL_SCAN_SOURCES:
                per_source[src] = (0, True)
            return {"mode": "legacy", "full_scan": True, "per_source": per_source}

        cfg = SCAN_MODE_CONFIG[normalized]

        if normalized == "full":
            for src in FULL_SCAN_SOURCES:
                per_source[src] = (0, True)
            return {"mode": "full", "full_scan": True, "per_source": per_source}

        if normalized == "custom":
            effective = max(1, min(500, int(limit_per_source or 1)))
        else:
            effective = int(cfg["limit"])

        return {"mode": normalized, "full_scan": False, "per_source": per_source, "limit": effective}

    @classmethod
    async def _execute_batch(
        cls,
        session: AsyncSession,
        limit_per_source: int = 50,
        context_dir: Optional[str] = None,
        candidate_id: Optional[uuid.UUID] = None,
        scan_mode: Optional[str] = None,
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
        expired_marked = 0
        expired_total = 0

        # Phase 2.8: Quy đổi scan_mode -> kế hoạch quét theo từng nguồn
        scan_plan = cls.resolve_scan_plan(scan_mode, limit_per_source)
        effective_scan_mode = scan_plan["mode"]
        effective_limit = scan_plan.get("limit", limit_per_source)
        full_scan_sources = sorted(
            src for src, (lim, is_full) in scan_plan["per_source"].items() if is_full
        )
        logger.info(
            f"🔍 Scan plan resolved: mode={effective_scan_mode} "
            f"(limit={effective_limit}, full_scan_sources={full_scan_sources})"
        )

        # 1. Xác định hoặc đồng bộ Candidate Profile
        logger.info("Step 1/5: Resolving Candidate Profile & Master Resume context...")
        try:
            if candidate_id:
                candidate = await CandidateRepository.get_by_id(session, candidate_id)
            else:
                # Thử đồng bộ từ /context nếu tồn tại (local Docker), bỏ qua nếu không có (cloud Render)
                import os
                resolved_context = context_dir or os.getenv("CONTEXT_DIR", "/context")
                if os.path.isdir(resolved_context):
                    await CandidateService.sync_profile_from_context(session, context_dir=resolved_context)
                    logger.info(f"Context directory found at '{resolved_context}', profile synced.")
                else:
                    logger.info(f"Context directory '{resolved_context}' not found (cloud deployment) — skipping sync, using existing DB profile.")
                candidate = await CandidateRepository.get_profile(session)

            if not candidate:
                raise ValueError("Candidate profile not found in database. Please upload a resume or sync profile first.")
            logger.info(f"✅ Candidate profile resolved: {candidate.full_name} ({candidate.headline})")
        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"❌ Failed to resolve candidate profile: {e}", exc_info=True)
            raise RuntimeError(f"Candidate profile resolution failed: {e}")

        # 2. Đồng bộ Skill Taxonomy
        logger.info("Step 2/5: Seeding and synchronizing Canonical Skill Taxonomy...")
        try:
            await skill_normalizer.seed_or_sync_db(session)
            logger.info("✅ Canonical Skill Taxonomy verified and synced.")
        except Exception as e:
            logger.warning(f"⚠️ Non-blocking warning during skill taxonomy sync: {e}")

        # 2b. Tinh gọn dữ liệu: Đánh dấu EXPIRED cho tin cũ quá 30 ngày (trừ tin đã Bookmark hoặc đã Nộp)
        try:
            from datetime import timedelta
            from sqlalchemy import update
            from app.models.saved_job import SavedJob
            from app.models.resume import ApplicationLog

            cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            saved_job_ids_stmt = select(SavedJob.job_id)
            app_job_ids_stmt = select(ApplicationLog.job_id)

            expire_stmt = (
                update(Job)
                .where(
                    Job.status == JobStatusEnum.ACTIVE,
                    Job.created_at < cutoff,
                    Job.id.notin_(saved_job_ids_stmt),
                    Job.id.notin_(app_job_ids_stmt),
                )
                .values(status=JobStatusEnum.EXPIRED)
            )
            res_expire = await session.execute(expire_stmt)
            if res_expire.rowcount:
                logger.info(f"🧹 Retention Policy: Auto-expired {res_expire.rowcount} stale jobs older than 30 days.")
                await session.commit()
        except Exception as e:
            logger.warning(f"⚠️ Non-blocking warning during stale jobs retention check: {e}")

        # 3. Thu thập Job mới từ các Collectors Đa trang có chủ đích IT (Zero LLM cost)
        logger.info("Step 3/5: Collecting new IT jobs from multi-page active sources (Zero LLM Cost)...")
        collectors = [
            RemotiveJobCollector(),
            ITViecJobCollector(),
            CareerLinkJobCollector(),
            TopCVJobCollector(),
            ITNaviJobCollector(),
            GrowUpWorkJobCollector(),
            VietnamWorksJobCollector(),
            UpworkJobCollector(),
            TopDevJobCollector(),
        ]

        for col in collectors:
            sources_scanned.append(col.source_name)

            if effective_scan_mode in ("full", "legacy"):
                if col.source_name in scan_plan["per_source"]:
                    col_limit, col_full_scan = scan_plan["per_source"][col.source_name]
                else:
                    # Nguồn ngoài (remote quốc tế): chưa hỗ trợ quét toàn bộ
                    col_limit = (
                        FOREIGN_SOURCE_FULL_SCAN_CAP
                        if effective_scan_mode == "full"
                        else limit_per_source
                    )
                    col_full_scan = False
            else:
                col_limit, col_full_scan = effective_limit, False

            try:
                stats: IngestionStats = await ingestion_pipeline.run(
                    collector=col,
                    db=session,
                    limit=col_limit,
                    use_llm=False,  # BẢO ĐẢM CHI PHÍ 0Đ
                    full_scan=col_full_scan,
                )
                total_fetched += stats.total_fetched
                new_jobs_created += stats.created
                unchanged_jobs += stats.unchanged
                duplicates_detected += stats.duplicates_detected
                ingestion_errors += stats.errors
                expired_marked += stats.expired_marked
            except Exception as e:
                logger.error(f"❌ Error during collection for source {col.source_name}: {e}", exc_info=True)
                ingestion_errors += 1

        # 3.5. Bảo trì hạn nộp: chuyển job ACTIVE đã quá hạn sang EXPIRED
        try:
            expired_total = await ingestion_pipeline.expire_outdated_jobs(session)
            if expired_total:
                logger.info(f"⌛ Retention: marked {expired_total} outdated jobs as EXPIRED.")
        except Exception as e:
            logger.warning(f"⚠️ Non-blocking warning during expiry maintenance: {e}")

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
            scan_mode=effective_scan_mode,
            full_scan_sources=full_scan_sources,
            sources_scanned=sources_scanned,
            total_fetched=total_fetched,
            new_jobs_created=new_jobs_created,
            unchanged_jobs=unchanged_jobs,
            duplicates_detected=duplicates_detected,
            ingestion_errors=ingestion_errors,
            expired_marked=expired_marked,
            expired_total=expired_total,
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
