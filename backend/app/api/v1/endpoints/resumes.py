import os
import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.limiter import limiter
from app.core.security import get_authenticated_user_or_internal
from app.schemas.resume import (
    TailorResumeRequest,
    TailoredResumeResponse,
    UpdateLatexRequest,
)
from app.services.tailoring.resume_service import resume_service

router = APIRouter()


@router.post("/tailor/{job_id}", response_model=TailoredResumeResponse)
@limiter.limit("5/minute")
async def tailor_resume(
    request: Request,
    job_id: uuid.UUID,
    payload: TailorResumeRequest = TailorResumeRequest(),
    db: AsyncSession = Depends(get_db),
    _user: Any = Depends(get_authenticated_user_or_internal),
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
    _user: Any = Depends(get_authenticated_user_or_internal),
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
    _user: Any = Depends(get_authenticated_user_or_internal),
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


import re
import unicodedata

def sanitize_header_filename(text: str) -> str:
    """Chuyển đổi tên có dấu tiếng Việt hoặc ký tự đặc biệt thành ASCII an toàn cho HTTP Header."""
    normalized = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    cleaned = re.sub(r'[^a-zA-Z0-9_\-]', '_', normalized).strip('_')
    return cleaned or "Document"


@router.get("/{id}/pdf")
async def download_resume_pdf(
    id: uuid.UUID,
    download: bool = Query(False, description="Nếu True sẽ trả về attachment để tải xuống, ngược lại inline để xem trước"),
    db: AsyncSession = Depends(get_db),
    _user: Any = Depends(get_authenticated_user_or_internal),
):
    """
    Xem trước hoặc tải về tệp tin PDF của CV đã được biên dịch hoàn chỉnh.
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

    cand_name = sanitize_header_filename(resume.candidate.full_name if resume.candidate else "Candidate")
    comp_name = sanitize_header_filename(resume.job.company_name if resume.job else "Company")
    filename = f"Resume_{cand_name}_{comp_name}.pdf"

    return FileResponse(
        path=resume.pdf_path,
        media_type="application/pdf",
        filename=filename,
        content_disposition_type="attachment" if download else "inline",
    )


@router.get("/{id}/tex")
async def get_resume_latex_source(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: Any = Depends(get_authenticated_user_or_internal),
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


@router.put("/{id}/tex", response_model=TailoredResumeResponse)
async def update_resume_latex_source(
    id: uuid.UUID,
    payload: UpdateLatexRequest,
    db: AsyncSession = Depends(get_db),
    _user: Any = Depends(get_authenticated_user_or_internal),
):
    """
    Cập nhật mã nguồn LaTeX (.tex) do người dùng chỉnh sửa và tự động biên dịch lại PDF.
    """
    try:
        updated_resume = await resume_service.update_and_recompile_latex(
            session=db,
            resume_id=id,
            new_latex_source=payload.latex_source,
        )
        return updated_resume
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Recompilation failed: {str(e)}",
        )


@router.delete("/job/{job_id}")
async def delete_tailored_resume_by_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: Any = Depends(get_authenticated_user_or_internal),
):
    """
    Xóa bản Tailored Resume và Cover Letter của một Job ID cụ thể để chuẩn bị sinh lại.
    """
    deleted = await resume_service.delete_tailored_resume_by_job_id(db, job_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No tailored resume found for job ID {job_id} to delete",
        )
    return {
        "status": "success",
        "message": f"Tailored resume and cover letter for job {job_id} deleted successfully.",
    }


@router.delete("/{id}")
async def delete_tailored_resume(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: Any = Depends(get_authenticated_user_or_internal),
):
    """
    Xóa bản Tailored Resume và Cover Letter theo ID.
    """
    deleted = await resume_service.delete_tailored_resume_by_id(db, id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tailored resume with ID {id} not found to delete",
        )
    return {
        "status": "success",
        "message": f"Tailored resume {id} deleted successfully.",
    }

