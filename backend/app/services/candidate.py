import uuid
from pathlib import Path
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.candidate import CandidateRepository
from app.schemas.candidate import (
    CandidateDetailResponse,
    CandidateSyncResponse,
    CandidateUpdate,
)
from app.services.parser import CandidateProfileParser


class CandidateService:
    """
    Service Layer điều phối các nghiệp vụ liên quan đến Hồ sơ Ứng viên:
    - Truy xuất thông tin chi tiết
    - Cập nhật thông tin nhanh
    - Đồng bộ hóa từ các tệp tin ngữ cảnh (context files)
    """

    @staticmethod
    def get_default_context_dir() -> Path:
        """Lấy đường dẫn mặc định tới thư mục context/ (hỗ trợ cả Docker container và Local host)."""
        docker_context = Path("/context")
        if docker_context.exists() and docker_context.is_dir():
            return docker_context
        # Local host: backend/app/services/candidate.py -> 4 cấp lên tới project root
        return Path(__file__).resolve().parent.parent.parent.parent / "context"

    @classmethod
    async def get_profile(cls, session: AsyncSession) -> CandidateDetailResponse:
        """
        Lấy thông tin hồ sơ ứng viên.
        Nếu chưa có hồ sơ trong database, tự động thử sync từ thư mục context/ nếu tồn tại.
        """
        candidate = await CandidateRepository.get_profile(session)
        if not candidate:
            context_dir = cls.get_default_context_dir()
            if context_dir.exists():
                parsed = CandidateProfileParser.load_and_merge_context(context_dir)
                candidate = await CandidateRepository.sync_from_parsed_context(session, parsed)

        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate profile not found. Please sync from context files first.",
            )

        return CandidateDetailResponse.model_validate(candidate)

    @classmethod
    async def update_profile(
        cls, session: AsyncSession, update_data: CandidateUpdate
    ) -> CandidateDetailResponse:
        """Cập nhật các trường thông tin của hồ sơ ứng viên hiện tại."""
        candidate = await CandidateRepository.get_profile(session)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate profile not found to update.",
            )

        updated_candidate = await CandidateRepository.update_profile_fields(
            session, candidate.id, update_data
        )
        return CandidateDetailResponse.model_validate(updated_candidate)

    @classmethod
    async def sync_profile_from_context(
        cls, session: AsyncSession, context_dir: Optional[Path | str] = None
    ) -> CandidateSyncResponse:
        """
        Kích hoạt đồng bộ hóa dữ liệu từ context/ (candidate-profile.yaml, master-resume.tex, master-resume.md).
        """
        target_dir = Path(context_dir) if context_dir else cls.get_default_context_dir()
        if not target_dir.exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Context directory does not exist: {target_dir}",
            )

        parsed = CandidateProfileParser.load_and_merge_context(target_dir)
        candidate = await CandidateRepository.sync_from_parsed_context(session, parsed)

        return CandidateSyncResponse(
            success=True,
            candidate_id=candidate.id,
            full_name=candidate.full_name,
            skills_count=len(candidate.skills),
            projects_count=len(candidate.projects),
            experiences_count=len(candidate.experiences),
            certifications_count=len(candidate.certifications),
            message="Candidate profile successfully synchronized from context files.",
        )
