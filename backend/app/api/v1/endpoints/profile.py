from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_internal_secret
from app.schemas.candidate import (
    CandidateDetailResponse,
    CandidateSyncResponse,
    CandidateUpdate,
)
from app.services.candidate import CandidateService

router = APIRouter()


@router.get(
    "",
    response_model=CandidateDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy chi tiết hồ sơ ứng viên",
    description="Truy xuất thông tin đầy đủ của ứng viên kèm theo danh sách kỹ năng, kinh nghiệm, dự án và bằng chứng định lượng.",
)
async def get_profile(
    db: AsyncSession = Depends(get_db),
    _authorized: bool = Depends(verify_internal_secret),
) -> CandidateDetailResponse:
    return await CandidateService.get_profile(db)


@router.put(
    "",
    response_model=CandidateDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Cập nhật hồ sơ ứng viên",
    description="Cập nhật các trường thông tin cơ bản của hồ sơ ứng viên (headline, mục tiêu, sở thích tuyển dụng...).",
)
async def update_profile(
    update_data: CandidateUpdate,
    db: AsyncSession = Depends(get_db),
    _authorized: bool = Depends(verify_internal_secret),
) -> CandidateDetailResponse:
    return await CandidateService.update_profile(db, update_data)


@router.post(
    "/sync",
    response_model=CandidateSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Đồng bộ hồ sơ từ context files",
    description="Đọc toàn bộ file trong thư mục context/ (candidate-profile.yaml, master-resume.tex, master-resume.md) và nạp mới vào PostgreSQL.",
)
async def sync_profile(
    db: AsyncSession = Depends(get_db),
    _authorized: bool = Depends(verify_internal_secret),
) -> CandidateSyncResponse:
    return await CandidateService.sync_profile_from_context(db)
