import secrets
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.limiter import limiter
from app.core.security import get_current_user_optional
from app.services.system_service import PurgeReport, system_service

router = APIRouter()


async def verify_admin_access(
    x_internal_secret: Optional[str] = Header(None, alias="X-Internal-Secret"),
    user: Optional[Any] = Depends(get_current_user_optional),
) -> bool:
    """Xác thực quyền quản trị hệ thống: yêu cầu X-Internal-Secret hợp lệ hoặc tài khoản Superuser."""
    if x_internal_secret:
        is_valid = secrets.compare_digest(
            x_internal_secret.encode("utf-8"),
            settings.INTERNAL_API_SECRET.encode("utf-8")
        )
        if is_valid:
            return True
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal API secret for system administrative operations",
        )

    if user and getattr(user, "is_superuser", False):
        return True

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Administrative privilege required for this system operation.",
    )


class PurgeRequest(BaseModel):
    scope: str = "jobs_and_tailoring"  # 'all', 'jobs_and_tailoring', 'tailoring_only', 'matches_only'
    clean_storage: bool = True
    confirm: bool = False


@router.post(
    "/purge-database",
    response_model=PurgeReport,
    summary="Xóa / Làm trống dữ liệu Database",
    description=(
        "Cho phép xóa dữ liệu theo các phạm vi:\n"
        "- `all`: Xóa tất cả Jobs, Matches, Resumes, Applications, Candidate Profiles.\n"
        "- `jobs_and_tailoring`: Xóa Jobs, Matches, Resumes, Applications (giữ Candidate Profile).\n"
        "- `tailoring_only`: Xóa Resumes, Cover Letters, Applications (giữ Jobs & Candidate).\n"
        "- `matches_only`: Xóa Job Matches để chấm điểm lại."
    ),
)
@limiter.limit("2/minute")
async def purge_database(
    request: Request,
    payload: PurgeRequest,
    db: AsyncSession = Depends(get_db),
    _auth: bool = Depends(verify_admin_access),
) -> PurgeReport:
    if not payload.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide confirm=true to acknowledge database purge.",
        )

    valid_scopes = ["all", "jobs_and_tailoring", "tailoring_only", "matches_only"]
    if payload.scope not in valid_scopes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scope '{payload.scope}'. Must be one of: {valid_scopes}",
        )

    return await system_service.purge_database(
        session=db,
        scope=payload.scope,
        clean_storage=payload.clean_storage,
    )


@router.post(
    "/reset-demo",
    summary="Reset toàn bộ hệ thống về trạng thái mẫu ban đầu",
    description="Xóa toàn bộ dữ liệu, nạp lại Skill Taxonomy và đồng bộ Profile từ context.example/.",
)
@limiter.limit("2/minute")
async def reset_demo(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _auth: bool = Depends(verify_admin_access),
) -> Dict[str, Any]:
    return await system_service.reset_demo(session=db)

