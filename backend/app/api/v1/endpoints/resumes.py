import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.resume import (
    TailorResumeRequest,
    TailoredResumeResponse,
)
from app.services.tailoring.resume_service import resume_service

router = APIRouter()


@router.post("/tailor/{job_id}", response_model=TailoredResumeResponse)
async def tailor_resume(
    job_id: uuid.UUID,
    payload: TailorResumeRequest = TailorResumeRequest(),
    db: AsyncSession = Depends(get_db),
):
    """
    Kích hoạt quy trình tinh chỉnh CV cho một tin tuyển dụng cụ thể:
    - Bám sát JD, tái cấu trúc LaTeX theo mẫu chuẩn.
    - Kiểm chứng tính xác thực Provenance Verification (Zero Hallucination).
    - Biên dịch tự động mã nguồn TeX sang tệp tin PDF.
    - Sinh Cover Letter Markdown chân thực và khiêm tốn.
    """
    try:
        resume = await resume_service.tailor_resume_for_job(
            session=db,
            job_id=job_id,
            candidate_id=payload.candidate_id,
            force_regenerate=payload.force_regenerate,
            custom_tone=payload.custom_tone or "professional_and_humble",
        )
        return resume
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Resume tailoring failed: {str(e)}",
        )


@router.get("/{id}", response_model=TailoredResumeResponse)
async def get_tailored_resume(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy thông tin chi tiết một bản Tailored Resume kèm bằng chứng Provenance và Cover Letter.
    """
    resume = await resume_service.get_tailored_resume_by_id(db, id)
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tailored resume with ID {id} not found",
        )
    return resume


@router.get("/job/{job_id}", response_model=TailoredResumeResponse)
async def get_tailored_resume_by_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy bản Tailored Resume đã sinh cho một Job ID cụ thể.
    """
    resume = await resume_service.get_tailored_resume_by_job_id(db, job_id)
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No tailored resume found for job {job_id}. Use POST /api/v1/resumes/tailor/{job_id} to generate one.",
        )
    return resume


@router.get("/{id}/pdf")
async def download_resume_pdf(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Tải về tệp tin PDF của CV đã được biên dịch hoàn chỉnh.
    """
    resume = await resume_service.get_tailored_resume_by_id(db, id)
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tailored resume with ID {id} not found",
        )

    if not resume.pdf_path or not os.path.exists(resume.pdf_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF artifact file not found on disk. Please trigger re-tailoring.",
        )

    filename = f"Resume_{resume.candidate.full_name.replace(' ', '_')}_{resume.job.company_name.replace(' ', '_')}.pdf"
    return FileResponse(
        path=resume.pdf_path,
        media_type="application/pdf",
        filename=filename,
    )


@router.get("/{id}/tex")
async def get_resume_latex_source(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy mã nguồn LaTeX (.tex) thô của Tailored Resume.
    """
    resume = await resume_service.get_tailored_resume_by_id(db, id)
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tailored resume with ID {id} not found",
        )

    return PlainTextResponse(
        content=resume.latex_source,
        media_type="text/plain",
    )
