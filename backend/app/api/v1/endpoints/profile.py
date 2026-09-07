from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_authenticated_user_or_internal, verify_admin_access
from app.models.user import User
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
    current_user: User = Depends(get_authenticated_user_or_internal),
) -> CandidateDetailResponse:
    return await CandidateService.get_profile(db, user_id=current_user.id)


@router.put(
    "",
    response_model=CandidateDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Cập nhật thông tin hồ sơ ứng viên",
    description="Cho phép chỉnh sửa các trường thông tin cơ bản: headline, phone, email, github, linkedin, location.",
)
async def update_profile(
    update_data: CandidateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_authenticated_user_or_internal),
) -> CandidateDetailResponse:
    return await CandidateService.update_profile(db, update_data, user_id=current_user.id)


@router.post(
    "/sync",
    response_model=CandidateSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Đồng bộ hồ sơ từ các tệp cấu hình context/ (Chỉ Quản trị viên)",
    description="Đọc toàn bộ file trong thư mục context/ trên server và nạp mới vào PostgreSQL cho tài khoản quản trị.",
)
async def sync_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_authenticated_user_or_internal),
    _admin: bool = Depends(verify_admin_access),
) -> CandidateSyncResponse:
    return await CandidateService.sync_profile_from_context(db, user_id=current_user.id)


@router.post(
    "/upload-resume",
    response_model=CandidateSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Tải lên và phân tích CV động (.pdf, .tex, .yaml, .md, .json)",
    description="Cho phép người dùng upload file CV (PDF, LaTeX, YAML, Markdown) để tự động trích xuất thông tin cá nhân, kỹ năng, dự án và cập nhật vào hệ thống.",
)
async def upload_resume(
    request: Request,
    file: UploadFile = File(..., description="File CV (.pdf, .tex, .yaml, .yml, .md, .json)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_authenticated_user_or_internal),
) -> CandidateSyncResponse:
    max_size = settings.MAX_RESUME_UPLOAD_SIZE

    # 1. Kiểm tra Content-Length header để từ chối sớm
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > max_size:
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail=f"File size exceeds maximum allowed limit of {max_size // (1024 * 1024)}MB.",
                )
        except (ValueError, TypeError):
            pass

    # 2. Kiểm tra file.size nếu spooled file đã có thông tin
    if file.size and file.size > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File size exceeds maximum allowed limit of {max_size // (1024 * 1024)}MB.",
        )

    # 3. Kiểm tra định dạng đuôi file
    filename = file.filename or "resume.pdf"
    ext = Path(filename).suffix.lower()
    allowed_extensions = {".pdf", ".tex", ".yaml", ".yml", ".md", ".json", ".txt"}
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Supported formats: {', '.join(sorted(allowed_extensions))}",
        )

    # 4. Đọc theo bounded chunks để chống tràn bộ nhớ (OOM / Unbounded Memory)
    chunk_size = 64 * 1024
    chunks: list[bytes] = []
    total_bytes = 0

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total_bytes += len(chunk)
        if total_bytes > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"File size exceeds maximum allowed limit of {max_size // (1024 * 1024)}MB.",
            )
        chunks.append(chunk)

    file_bytes = b"".join(chunks)
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # 5. Xác thực nội dung thực tế (không chỉ tin tưởng extension)
    if ext == ".pdf":
        if not file_bytes.startswith(b"%PDF"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid PDF file format. The file header does not match PDF signature.",
            )
    else:
        # File văn bản (yaml, tex, md, json, txt) không được chứa null byte trong phần đầu
        if b"\x00" in file_bytes[:1024]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid text format. Binary data detected.",
            )

    return await CandidateService.ingest_resume_file(
        session=db,
        filename=filename,
        file_bytes=file_bytes,
        user_id=current_user.id,
    )
