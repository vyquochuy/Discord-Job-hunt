import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.resume import (
    ApplicationLogResponse,
    ApplicationStatusUpdateRequest,
    ApplicationSubmitRequest,
)
from app.services.tailoring.application_service import application_service

router = APIRouter()


@router.post("/apply/{job_id}", response_model=ApplicationLogResponse)
async def submit_job_application(
    job_id: uuid.UUID,
    payload: ApplicationSubmitRequest = ApplicationSubmitRequest(),
    db: AsyncSession = Depends(get_db),
):
    """
    Nộp hồ sơ ứng tuyển cho công việc:
    - Tự động chuẩn bị Tailored Resume và Cover Letter nếu chưa có.
    - Gửi email kèm file PDF CV (hoặc lưu Draft nếu simulate_only=True).
    - Cập nhật nhật ký ApplicationLog và chuyển trạng thái tin sang APPLIED.
    """
    try:
        app_log = await application_service.submit_application(
            session=db,
            job_id=job_id,
            channel=payload.channel,
            recipient_email=payload.recipient_email,
            subject=payload.subject,
            body=payload.body,
            simulate_only=payload.simulate_only,
        )
        return app_log
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Application submission failed: {str(e)}",
        )


@router.get("", response_model=List[ApplicationLogResponse])
async def list_applications(
    page: int = Query(1, ge=1, description="Số trang"),
    page_size: int = Query(20, ge=1, le=100, description="Kích thước trang"),
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy danh sách các đơn ứng tuyển đã nộp/chuẩn bị.
    """
    items, total = await application_service.list_applications(
        session=db,
        page=page,
        page_size=page_size,
    )
    return items


@router.get("/{id}", response_model=ApplicationLogResponse)
async def get_application_detail(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy thông tin chi tiết của một đơn ứng tuyển.
    """
    app_log = await application_service.get_application_by_id(db, id)
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
):
    """
    Cập nhật trạng thái đơn ứng tuyển (DRAFT, READY, SENT, INTERVIEW, OFFER, REJECTED).
    """
    app_log = await application_service.update_application_status(
        session=db,
        app_id=id,
        new_status=payload.status,
        error_message=payload.error_message,
    )
    if not app_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with ID {id} not found",
        )
    return app_log

