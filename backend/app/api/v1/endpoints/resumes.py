import logging
import os
import re
import unicodedata
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.limiter import limiter
from app.core.security import get_authenticated_user_or_internal
from app.models.candidate import Candidate
from app.models.resume import TailoredResume
from app.models.user import User
from app.repositories.candidate import CandidateRepository
from app.schemas.resume import (
    TailorResumeRequest,
    TailoredResumeResponse,
    UpdateLatexRequest,
)
from app.services.tailoring.resume_service import resume_service

logger = logging.getLogger("resumes")
router = APIRouter()


async def get_candidate_for_current_user(
    db: AsyncSession, current_user: User
) -> Candidate:
    """
    Resolve Candidate sở hữu bởi current_user.
    Nếu chưa có, tự động bootstrap 1-1 Candidate cho user đó.
    """
    candidate = await CandidateRepository.get_profile_by_user(db, current_user.id)
    if not candidate:
        candidate = await CandidateRepository.get_or_create_for_user(
            db, current_user.id, full_name=current_user.full_name, email=current_user.email
        )
    return candidate


def verify_resume_ownership(
    resume: TailoredResume, candidate: Candidate, user: User
) -> None:
    """
    Xác minh quyền sở hữu bản Tailored Resume (Chống IDOR).
    Nếu không phải chủ sở hữu và không phải Superuser, từ chối với HTTP 404.
    """
    if not user.is_superuser and resume.candidate_id != candidate.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tailored resume not found",
        )


def sanitize_header_filename(text: str) -> str:
    """Chuyển đổi tên có dấu tiếng Việt hoặc ký tự đặc biệt thành ASCII an toàn cho HTTP Header."""
    normalized = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    cleaned = re.sub(r'[^a-zA-Z0-9_\-]', '_', normalized).strip('_')
    return cleaned or "Document"


@router.post("/tailor/{job_id}", response_model=TailoredResumeResponse)
@limiter.limit("5/minute")
async def tailor_resume(
    request: Request,
    job_id: uuid.UUID,
    payload: TailorResumeRequest = TailorResumeRequest(),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_authenticated_user_or_internal),
):
    """
    Kích hoạt quy trình tinh chỉnh CV cho một tin tuyển dụng cụ thể:
    - Bám sát JD, tái cấu trúc LaTeX theo mẫu chuẩn.
    - Kiểm chứng tính xác thực Provenance Verification (Zero Hallucination).
    - Biên dịch tự động mã nguồn TeX sang tệp tin PDF trong sandbox riêng biệt.
    - Sinh Cover Letter Markdown chân thực và khiêm tốn.
    """
    try:
        cand = await get_candidate_for_current_user(db, _user)
        # Client không được phép inject candidate_id tùy tiện (chỉ superuser mới được chỉ định)
        target_candidate_id = payload.candidate_id if (_user.is_superuser and payload.candidate_id) else cand.id

        resume = await resume_service.tailor_resume_for_job(
            session=db,
            job_id=job_id,
            candidate_id=target_candidate_id,
            force_regenerate=payload.force_regenerate,
            custom_tone=payload.custom_tone or "professional_and_humble",
        )
        return resume
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception:
        logger.exception("Resume tailoring failed for job_id=%s", job_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred while tailoring resume.",
        )


@router.get("/{id}", response_model=TailoredResumeResponse)
async def get_tailored_resume(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_authenticated_user_or_internal),
):
    """
    Lấy thông tin chi tiết một bản Tailored Resume kèm bằng chứng Provenance và Cover Letter.
    Bảo vệ chống truy cập chéo (Anti-IDOR).
    """
    cand = await get_candidate_for_current_user(db, _user)
    resume = await resume_service.get_tailored_resume_by_id(db, id)
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tailored resume with ID {id} not found",
        )
    verify_resume_ownership(resume, cand, _user)
    return resume


@router.get("/job/{job_id}", response_model=TailoredResumeResponse)
async def get_tailored_resume_by_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_authenticated_user_or_internal),
):
    """
    Lấy bản Tailored Resume đã sinh cho một Job ID cụ thể của người dùng hiện tại.
    """
    cand = await get_candidate_for_current_user(db, _user)
    resume = await resume_service.get_tailored_resume_by_job_id(db, job_id, candidate_id=cand.id)
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No tailored resume found for job {job_id}. Use POST /api/v1/resumes/tailor/{job_id} to generate one.",
        )
    return resume


@router.get("/{id}/pdf")
async def download_resume_pdf(
    id: uuid.UUID,
    download: bool = Query(False, description="Nếu True sẽ trả về attachment để tải xuống, ngược lại inline để xem trước"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_authenticated_user_or_internal),
):
    """
    Xem trước hoặc tải về tệp tin PDF của CV đã được biên dịch hoàn chỉnh.
    Bảo vệ bằng xác thực tài khoản và kiểm tra quyền sở hữu.
    """
    cand = await get_candidate_for_current_user(db, _user)
    resume = await resume_service.get_tailored_resume_by_id(db, id)
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tailored resume with ID {id} not found",
        )
    verify_resume_ownership(resume, cand, _user)

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
    _user: User = Depends(get_authenticated_user_or_internal),
):
    """
    Lấy mã nguồn LaTeX (.tex) thô của Tailored Resume.
    """
    cand = await get_candidate_for_current_user(db, _user)
    resume = await resume_service.get_tailored_resume_by_id(db, id)
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tailored resume with ID {id} not found",
        )
    verify_resume_ownership(resume, cand, _user)

    return PlainTextResponse(
        content=resume.latex_source,
        media_type="text/plain",
    )


@router.put("/{id}/tex", response_model=TailoredResumeResponse)
async def update_resume_latex_source(
    id: uuid.UUID,
    payload: UpdateLatexRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_authenticated_user_or_internal),
):
    """
    Cập nhật mã nguồn LaTeX (.tex) do người dùng chỉnh sửa và tự động biên dịch lại PDF.
    """
    cand = await get_candidate_for_current_user(db, _user)
    resume = await resume_service.get_tailored_resume_by_id(db, id)
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tailored resume with ID {id} not found",
        )
    verify_resume_ownership(resume, cand, _user)

    try:
        updated_resume = await resume_service.update_and_recompile_latex(
            session=db,
            resume_id=id,
            new_latex_source=payload.latex_source,
            candidate_id=cand.id,
        )
        return updated_resume
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception:
        logger.exception("Resume recompilation failed for resume_id=%s", id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred while recompiling resume.",
        )


@router.delete("/job/{job_id}")
async def delete_tailored_resume_by_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_authenticated_user_or_internal),
):
    """
    Xóa bản Tailored Resume và Cover Letter của một Job ID cụ thể thuộc người dùng hiện tại.
    """
    cand = await get_candidate_for_current_user(db, _user)
    deleted = await resume_service.delete_tailored_resume_by_job_id(db, job_id, candidate_id=cand.id)
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
    _user: User = Depends(get_authenticated_user_or_internal),
):
    """
    Xóa bản Tailored Resume và Cover Letter theo ID (có xác thực quyền sở hữu).
    """
    cand = await get_candidate_for_current_user(db, _user)
    deleted = await resume_service.delete_tailored_resume_by_id(
        db, id, candidate_id=cand.id if not _user.is_superuser else None
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tailored resume with ID {id} not found to delete",
        )
    return {
        "status": "success",
        "message": f"Tailored resume {id} deleted successfully.",
    }
