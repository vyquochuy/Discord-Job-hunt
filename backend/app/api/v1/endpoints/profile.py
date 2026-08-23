import secrets
from typing import Optional, Any
from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user_optional
from app.schemas.candidate import (
    CandidateDetailResponse,
    CandidateSyncResponse,
    CandidateUpdate,
)
from app.services.candidate import CandidateService

router = APIRouter()


async def verify_profile_access(
    x_internal_secret: Optional[str] = Header(None, alias="X-Internal-Secret"),
    user: Optional[Any] = Depends(get_current_user_optional),
) -> bool:
    """
    Cho phép truy cập profile từ Web App hoặc Discord Bot có X-Internal-Secret.
    """
    if x_internal_secret:
        is_valid = secrets.compare_digest(
            x_internal_secret.encode("utf-8"),
            settings.INTERNAL_API_SECRET.encode("utf-8")
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid internal API secret",
            )
    return True


@router.get(
    "",
    response_model=CandidateDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy chi tiết hồ sơ ứng viên",
    description="Truy xuất thông tin đầy đủ của ứng viên kèm theo danh sách kỹ năng, kinh nghiệm, dự án và bằng chứng định lượng.",
)
async def get_profile(
    db: AsyncSession = Depends(get_db),
    _authorized: bool = Depends(verify_profile_access),
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
    _authorized: bool = Depends(verify_profile_access),
) -> CandidateDetailResponse:
    return await CandidateService.update_profile(db, update_data)


@router.post(
    "/sync",
    response_model=CandidateSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Đồng bộ hồ sơ từ context files",
    description="Đọc toàn bộ file trong thư mục context/ (candidate-profile.yaml, master-resume.tex, master-resume.md, master-resume.pdf) hoặc context.example/ và nạp mới vào PostgreSQL.",
)
async def sync_profile(
    db: AsyncSession = Depends(get_db),
    _authorized: bool = Depends(verify_profile_access),
) -> CandidateSyncResponse:
    return await CandidateService.sync_profile_from_context(db)


@router.post(
    "/upload-resume",
    response_model=CandidateSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Tải lên và phân tích CV động (.pdf, .tex, .yaml, .md, .json)",
    description="Cho phép người dùng upload file CV (PDF, LaTeX, YAML, Markdown) để tự động trích xuất thông tin cá nhân, kỹ năng, dự án và cập nhật vào hệ thống.",
)
async def upload_resume(
    file: UploadFile = File(..., description="File CV (.pdf, .tex, .yaml, .yml, .md, .json)"),
    db: AsyncSession = Depends(get_db),
    _authorized: bool = Depends(verify_profile_access),
) -> CandidateSyncResponse:
    file_bytes = await file.read()
    return await CandidateService.ingest_resume_file(
        session=db,
        filename=file.filename or "resume.pdf",
        file_bytes=file_bytes,
    )
