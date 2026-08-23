import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import (
    Candidate,
    CandidateCertification,
    CandidateExperience,
    CandidateProject,
    CandidateSkill,
)
from app.models.job import Job, JobSkill, RawJob
from app.models.match import JobMatch
from app.models.resume import (
    ApplicationLog,
    CoverLetter,
    EvidenceMap,
    TailoredResume,
)
from app.models.saved_job import SavedJob
from app.models.user import User
from app.services.candidate import CandidateService
from app.services.normalization.skill_normalizer import skill_normalizer

logger = logging.getLogger("system_service")


class PurgeReport(BaseModel):
    status: str = "success"
    scope: str
    cleaned_storage: bool
    deleted_counts: Dict[str, int] = {}
    message: str


class SystemService:
    """
    Dịch vụ quản trị hệ thống:
    - Làm trống / Xóa Database (Purge / Clean Data) theo phạm vi an toàn.
    - Dọn dẹp tệp tin lưu trữ (Storage Artifacts: PDF, TeX, MD).
    - Reset Demo: Dọn dẹp và nạp lại Profile mẫu + Skill Taxonomy.
    """

    @staticmethod
    def clean_storage_artifacts() -> int:
        """Dọn dẹp toàn bộ tệp tin PDF/TeX/MD tạm trong thư mục storage/resumes."""
        storage_root = Path(__file__).resolve().parent.parent.parent / "storage"
        removed_count = 0
        if storage_root.exists():
            for sub_dir in ["resumes", "tailored_resumes"]:
                target = storage_root / sub_dir
                if target.exists() and target.is_dir():
                    for item in target.iterdir():
                        try:
                            if item.is_dir():
                                shutil.rmtree(item, ignore_errors=True)
                            else:
                                item.unlink(missing_ok=True)
                            removed_count += 1
                        except Exception as e:
                            logger.warning(f"Error removing storage artifact {item}: {e}")
        return removed_count

    @classmethod
    async def purge_database(
        cls,
        session: AsyncSession,
        scope: str = "all",
        clean_storage: bool = True,
    ) -> PurgeReport:
        """
        Xóa dữ liệu database theo phạm vi:
        - 'all': Xóa toàn bộ Jobs, Matches, Resumes, Applications, Saved Jobs, Candidate Profile (giữ Users).
        - 'jobs_and_tailoring': Xóa Jobs, Matches, Resumes, Applications (giữ Candidate Profile & Taxonomy).
        - 'tailoring_only': Xóa Resumes, Cover Letters, Applications, Evidence Maps (giữ Jobs & Candidate).
        - 'matches_only': Xóa bảng JobMatch để tính điểm lại từ đầu.
        """
        logger.warning(f"Purging database with scope='{scope}', clean_storage={clean_storage}...")
        deleted_counts: Dict[str, int] = {}

        # 1. Luôn xóa các bảng Tailoring nếu scope là 'tailoring_only', 'jobs_and_tailoring', hoặc 'all'
        if scope in ["all", "jobs_and_tailoring", "tailoring_only"]:
            res_app = await session.execute(delete(ApplicationLog))
            deleted_counts["application_logs"] = res_app.rowcount or 0

            res_cov = await session.execute(delete(CoverLetter))
            deleted_counts["cover_letters"] = res_cov.rowcount or 0

            res_ev = await session.execute(delete(EvidenceMap))
            deleted_counts["evidence_maps"] = res_ev.rowcount or 0

            res_res = await session.execute(delete(TailoredResume))
            deleted_counts["tailored_resumes"] = res_res.rowcount or 0

        # 2. Xóa Matches
        if scope in ["all", "jobs_and_tailoring", "matches_only"]:
            res_mat = await session.execute(delete(JobMatch))
            deleted_counts["job_matches"] = res_mat.rowcount or 0

        # 3. Xóa Jobs & Raw Jobs
        if scope in ["all", "jobs_and_tailoring"]:
            res_sav = await session.execute(delete(SavedJob))
            deleted_counts["saved_jobs"] = res_sav.rowcount or 0

            res_jsk = await session.execute(delete(JobSkill))
            deleted_counts["job_skills"] = res_jsk.rowcount or 0

            res_job = await session.execute(delete(Job))
            deleted_counts["jobs"] = res_job.rowcount or 0

            res_raw = await session.execute(delete(RawJob))
            deleted_counts["raw_jobs"] = res_raw.rowcount or 0

        # 4. Xóa Candidate Profile
        if scope == "all":
            res_csk = await session.execute(delete(CandidateSkill))
            deleted_counts["candidate_skills"] = res_csk.rowcount or 0

            res_cex = await session.execute(delete(CandidateExperience))
            deleted_counts["candidate_experiences"] = res_cex.rowcount or 0

            res_cpr = await session.execute(delete(CandidateProject))
            deleted_counts["candidate_projects"] = res_cpr.rowcount or 0

            res_cce = await session.execute(delete(CandidateCertification))
            deleted_counts["candidate_certifications"] = res_cce.rowcount or 0

            res_cand = await session.execute(delete(Candidate))
            deleted_counts["candidates"] = res_cand.rowcount or 0

        await session.commit()

        # 5. Dọn dẹp Storage trên đĩa nếu được yêu cầu
        storage_cleaned = False
        if clean_storage and scope in ["all", "jobs_and_tailoring", "tailoring_only"]:
            cls.clean_storage_artifacts()
            storage_cleaned = True

        logger.info(f"Database purge completed successfully: {deleted_counts}")

        return PurgeReport(
            status="success",
            scope=scope,
            cleaned_storage=storage_cleaned,
            deleted_counts=deleted_counts,
            message=f"Database successfully purged with scope '{scope}'.",
        )

    @classmethod
    async def reset_demo(cls, session: AsyncSession) -> Dict[str, Any]:
        """
        Reset toàn bộ hệ thống về trạng thái ban đầu:
        1. Xóa dữ liệu cũ (Purge all).
        2. Nạp lại Canonical Skill Taxonomy.
        3. Đồng bộ lại Candidate Profile từ context/ hoặc context.example/.
        """
        purge_rep = await cls.purge_database(session, scope="all", clean_storage=True)

        # Sync Skill Taxonomy
        await skill_normalizer.seed_or_sync_db(session)

        # Sync Candidate Profile
        sync_res = await CandidateService.sync_profile_from_context(session)

        return {
            "status": "success",
            "message": "System successfully reset and re-seeded.",
            "purge_summary": purge_rep.model_dump(),
            "candidate_profile": sync_res.model_dump(),
        }


system_service = SystemService()
