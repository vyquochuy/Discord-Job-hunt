import logging
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_authenticated_user_or_internal
from app.models.candidate import Candidate
from app.models.user import User
from app.repositories.candidate import CandidateRepository
from app.schemas.resume import (
    ApplicationLogResponse,
    ApplicationStatusUpdateRequest,
    ApplicationSubmitRequest,
)
from app.services.tailoring.application_service import application_service

logger = logging.getLogger("applications")
router = APIRouter()


async def get_candidate_for_current_user(
    db: AsyncSession, current_user: User
) -> Candidate:
    candidate = await CandidateRepository.get_profile_by_user(db, current_user.id)
    if not candidate:
        candidate = await CandidateRepository.get_or_create_for_user(
            db, current_user.id, full_name=current_user.full_name, email=current_user.email
        )
    return candidate


@router.post("/apply/{job_id}", response_model=ApplicationLogResponse)
async def submit_job_application(
    job_id: uuid.UUID,
    payload: ApplicationSubmitRequest = ApplicationSubmitRequest(),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_authenticated_user_or_internal),
):
    """
    Nộp hồ sơ ứng tuyển cho công việc cho người dùng hiện tại:
    - Tự động chuẩn bị Tailored Resume và Cover Letter nếu chưa có.
    - Gửi email kèm file PDF CV (hoặc lưu Draft nếu simulate_only=True).
    - Cập nhật nhật ký ApplicationLog và chuyển trạng thái tin sang APPLIED.
    """
    try:
        cand = await get_candidate_for_current_user(db, _user)
        app_log = await application_service.submit_application(
            session=db,
            job_id=job_id,
            candidate_id=cand.id,
            channel=payload.channel,
            recipient_email=payload.recipient_email,
            subject=payload.subject,
            body=payload.body,
            simulate_only=payload.simulate_only,
        )
        return app_log
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception:
        logger.exception("Application submission failed for job_id=%s", job_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred while submitting application.",
        )


@router.get("", response_model=List[ApplicationLogResponse])
async def list_applications(
    all_users: bool = Query(False, description="Dành cho Quản trị viên xem toàn bộ đơn của mọi người"),
    page: int = Query(1, ge=1, description="Số trang"),
    page_size: int = Query(20, ge=1, le=100, description="Kích thước trang"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_authenticated_user_or_internal),
):
    """
    Lấy danh sách các đơn ứng tuyển đã nộp/chuẩn bị của người dùng hiện tại.
    """
    cand = await get_candidate_for_current_user(db, _user)
    filter_cand_id = None if (_user.is_superuser and all_users) else cand.id
    items, total = await application_service.list_applications(
        session=db,
        candidate_id=filter_cand_id,
        page=page,
        page_size=page_size,
    )
    return items


@router.get("/{id}", response_model=ApplicationLogResponse)
async def get_application_detail(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_authenticated_user_or_internal),
):
    """
    Lấy thông tin chi tiết của một đơn ứng tuyển (có kiểm tra quyền sở hữu).
    """
    cand = await get_candidate_for_current_user(db, _user)
    app_log = await application_service.get_application_by_id(
        db, id, candidate_id=cand.id if not _user.is_superuser else None
    )
    if not app_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with ID {id} not found",
        )
    return app_log


@router.patch("/{id}/status", response_model=ApplicationLogResponse)
async def update_application_status(
    id: uuid.UUID,
    payload: ApplicationStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_authenticated_user_or_internal),
):
    """
    Cập nhật trạng thái đơn ứng tuyển (DRAFT, READY, SENT, INTERVIEW, OFFER, REJECTED)
    (có kiểm tra quyền sở hữu).
    """
    cand = await get_candidate_for_current_user(db, _user)
    app_log = await application_service.update_application_status(
        session=db,
        app_id=id,
        new_status=payload.status,
        error_message=payload.error_message,
        candidate_id=cand.id if not _user.is_superuser else None,
    )
    if not app_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with ID {id} not found",
        )
    return app_log
