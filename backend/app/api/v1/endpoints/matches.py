import asyncio
import uuid
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_authenticated_user_or_internal
from app.api.v1.endpoints.system import verify_admin_access
from app.schemas.match import (
    BatchCalculateResponse,
    JobMatchDetailResponse,
    JobMatchResponse,
    MatchListResponse,
    TopRecommendationItem,
)
from app.services.matching.match_service import job_match_service
from app.services.matching.models import Eligibility, RecommendationCategory

router = APIRouter()


@router.get("", response_model=MatchListResponse)
async def list_matches(
    min_score: Optional[float] = Query(None, ge=0.0, le=100.0, description="Lọc theo điểm số tối thiểu"),
    eligibility: Optional[Eligibility] = Query(None, description="Lọc theo tư cách: ELIGIBLE, BLOCKED, UNCERTAIN"),
    recommendation: Optional[RecommendationCategory] = Query(None, description="Lọc theo phân loại khuyến nghị"),
    page: int = Query(1, ge=1, description="Số trang (bắt đầu từ 1)"),
    page_size: int = Query(20, ge=1, le=100, description="Số lượng bản ghi mỗi trang"),
    db: AsyncSession = Depends(get_db),
    _user: Any = Depends(get_authenticated_user_or_internal),
):
    """
    Lấy danh sách các tin tuyển dụng đã được phân tích mức độ phù hợp (Job Matches).
    """
    try:
        items, total = await job_match_service.list_matches(
            db,
            min_score=min_score,
            eligibility=eligibility,
            recommendation=recommendation,
            page=page,
            page_size=page_size,
        )
        return MatchListResponse(
            items=[JobMatchResponse.model_validate(m) for m in items],
            total=total,
            page=page,
            page_size=page_size,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/recommendations/top", response_model=List[TopRecommendationItem])
async def get_top_recommendations(
    limit: int = Query(10, ge=1, le=50, description="Số lượng gợi ý tối đa"),
    min_score: float = Query(60.0, ge=0.0, le=100.0, description="Điểm số tối thiểu"),
    db: AsyncSession = Depends(get_db),
    _user: Any = Depends(get_authenticated_user_or_internal),
):
    """
    Lấy danh sách các công việc được đề xuất hàng đầu (Top Recommendations) cho ứng viên.
    Loại bỏ các công việc bị BLOCKED bởi Hard Filters.
    """
    try:
        matches = await job_match_service.get_top_recommendations(
            db, limit=limit, min_score=min_score
        )

        results: List[TopRecommendationItem] = []
        for m in matches:
            if m.job:
                results.append(
                    TopRecommendationItem(
                        job_id=m.job.id,
                        title=m.job.title,
                        company_name=m.job.company_name,
                        location=m.job.normalized_location or m.job.location,
                        work_mode=m.job.work_mode,
                        level=m.job.level,
                        min_salary=m.job.min_salary,
                        max_salary=m.job.max_salary,
                        salary_currency=m.job.salary_currency,
                        score=m.score,
                        eligibility=m.eligibility,
                        recommendation=m.recommendation,
                        matched_skills=m.matched_skills or [],
                        missing_required_skills=m.missing_required_skills or [],
                        source=m.job.source,
                        source_url=m.job.source_url,
                        posted_at=m.job.posted_at,
                    )
                )


        return results
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{job_id}", response_model=JobMatchDetailResponse)
async def get_job_match(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: Any = Depends(get_authenticated_user_or_internal),
):
    """
    Lấy kết quả chi tiết phân tích match của 1 tin tuyển dụng (bao gồm 7 signals, hard filters và AI explanation).
    Nếu chưa từng tính toán, hệ thống sẽ tự động tính toán và lưu lại.
    """
    try:
        match_obj = await job_match_service.calculate_match_for_job(
            db, job_id, force_refresh=False
        )
        return JobMatchDetailResponse.model_validate(match_obj)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/calculate/{job_id}", response_model=JobMatchDetailResponse)
async def calculate_match(
    job_id: uuid.UUID,
    force_refresh: bool = Query(True, description="Bắt buộc tính toán lại, bỏ qua cache"),
    db: AsyncSession = Depends(get_db),
    _user: Any = Depends(get_authenticated_user_or_internal),
):
    """
    Kích hoạt tính toán phân tích độ phù hợp cho một tin tuyển dụng theo yêu cầu.
    """
    try:
        match_obj = await job_match_service.calculate_match_for_job(
            db, job_id, force_refresh=force_refresh
        )
        return JobMatchDetailResponse.model_validate(match_obj)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/calculate-all", response_model=BatchCalculateResponse)
async def calculate_all_matches(
    db: AsyncSession = Depends(get_db),
    _auth: bool = Depends(verify_admin_access),
):
    """
    Kích hoạt tính toán lại độ phù hợp cho toàn bộ các tin tuyển dụng đang ACTIVE (Yêu cầu quyền Quản trị).
    """
    try:
        total = await job_match_service.batch_calculate_all(db)
        return BatchCalculateResponse(
            status="completed",
            total_jobs=total,
            message=f"Đã hoàn thành tính toán độ phù hợp cho {total} tin tuyển dụng.",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
