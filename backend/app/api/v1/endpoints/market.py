from datetime import date
from typing import Literal, Optional, Set

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.job import JobLevelEnum, SkillCategoryEnum, WorkModeEnum
from app.schemas.market import (
    EmployersResponse,
    GeographyResponse,
    HiringTrendsResponse,
    InsightsResponse,
    MarketAnalyticsResponse,
    MarketFilterCatalogResponse,
    OverviewResponse,
    RolesResponse,
    SalaryResponse,
    SkillsResponse,
)
from app.services.analytics.catalog import get_filter_catalog
from app.services.analytics.employer_intelligence import get_employer_intelligence
from app.services.analytics.filters import MarketFilters
from app.services.analytics.geography_intelligence import get_geography_intelligence
from app.services.analytics.hiring_trends import get_hiring_trends
from app.services.analytics.insight_engine import get_insights
from app.services.analytics.market_analytics import get_market_analytics
from app.services.analytics.overview import get_overview
from app.services.analytics.role_intelligence import get_role_intelligence
from app.services.analytics.salary_intelligence import get_salary_intelligence
from app.services.analytics.skills_intelligence import get_skills_intelligence
from app.services.analytics.taxonomy import CATEGORY_LABELS, REGION_LABELS

router = APIRouter()

LEVEL_VALUES: Set[str] = {member.value for member in JobLevelEnum}
WORK_MODE_VALUES: Set[str] = {member.value for member in WorkModeEnum}
SKILL_CATEGORY_VALUES: Set[str] = {member.value for member in SkillCategoryEnum}


class MarketFilterParams:
    """Shared query parameters for every market analytics endpoint."""

    def __init__(
        self,
        date_from: Optional[date] = Query(None, description="Ngày bắt đầu (YYYY-MM-DD), dựa trên posted_at."),
        date_to: Optional[date] = Query(None, description="Ngày kết thúc (YYYY-MM-DD), bao gồm cả ngày này."),
        category: Optional[str] = Query(None, max_length=255, description="Nhóm nghề suy ra (derived category)."),
        level: Optional[str] = Query(None, max_length=255, description="Cấp bậc đã chuẩn hóa."),
        location: Optional[str] = Query(None, max_length=255, description="Giá trị normalized_location chính xác."),
        region: Optional[str] = Query(None, max_length=255, description="Vùng suy ra (derived region)."),
        source: Optional[str] = Query(None, max_length=255, description="Nguồn ingestion (itviec, topcv, ...)."),
        work_mode: Optional[str] = Query(None, max_length=255, description="ONSITE | HYBRID | REMOTE."),
        skill: Optional[str] = Query(None, max_length=255, description="Tên kỹ năng chuẩn (canonical skill)."),
        company: Optional[str] = Query(None, max_length=255, description="Tên công ty đã chuẩn hóa."),
        include_expired: bool = Query(False, description="Bao gồm tin EXPIRED; MERGED luôn bị loại."),
    ) -> None:
        self.date_from = date_from
        self.date_to = date_to
        self.category = category
        self.level = level
        self.location = location
        self.region = region
        self.source = source
        self.work_mode = work_mode
        self.skill = skill
        self.company = company
        self.include_expired = include_expired

    def to_filters(self) -> MarketFilters:
        # Bound explicit daily charts; never silently truncate requested history.
        if self.date_to == date.max or self.date_from == date.min:
            raise HTTPException(status_code=422, detail="Date is outside the supported range.")
        if self.date_from and self.date_to and (self.date_to - self.date_from).days > 3660:
            raise HTTPException(status_code=422, detail="Date range cannot exceed 10 years.")
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise HTTPException(
                status_code=422,
                detail="date_from phải nhỏ hơn hoặc bằng date_to.",
            )
        if self.category and self.category not in CATEGORY_LABELS:
            raise HTTPException(
                status_code=422,
                detail=f"category không hợp lệ: {self.category}",
            )
        if self.level and self.level not in LEVEL_VALUES:
            raise HTTPException(
                status_code=422,
                detail=f"level không hợp lệ: {self.level}",
            )
        if self.work_mode and self.work_mode not in WORK_MODE_VALUES:
            raise HTTPException(
                status_code=422,
                detail=f"work_mode không hợp lệ: {self.work_mode}",
            )
        if self.region and self.region not in REGION_LABELS:
            raise HTTPException(
                status_code=422,
                detail=f"region không hợp lệ: {self.region}",
            )
        return MarketFilters(
            date_from=self.date_from,
            date_to=self.date_to,
            category=self.category,
            level=self.level,
            location=self.location,
            region=self.region,
            source=self.source,
            work_mode=self.work_mode,
            skill=self.skill,
            company=self.company,
            include_expired=self.include_expired,
        )


@router.get("/analytics", response_model=MarketAnalyticsResponse)
async def market_analytics(db: AsyncSession = Depends(get_db)):
    """Legacy endpoint kept for backward compatibility."""
    return await get_market_analytics(db)


@router.get("/filters", response_model=MarketFilterCatalogResponse)
async def market_filters(db: AsyncSession = Depends(get_db)):
    return await get_filter_catalog(db)


@router.get("/overview", response_model=OverviewResponse)
async def market_overview(
    params: MarketFilterParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    return await get_overview(db, params.to_filters())


@router.get("/hiring-trends", response_model=HiringTrendsResponse)
async def market_hiring_trends(
    params: MarketFilterParams = Depends(),
    granularity: Literal["auto", "day", "week", "month"] = Query(
        "auto", description="Độ chi tiết thời gian; auto tự chọn theo độ dài khoảng."
    ),
    db: AsyncSession = Depends(get_db),
):
    return await get_hiring_trends(db, params.to_filters(), granularity)


@router.get("/salaries", response_model=SalaryResponse)
async def market_salaries(
    params: MarketFilterParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    return await get_salary_intelligence(db, params.to_filters())


@router.get("/skills", response_model=SkillsResponse)
async def market_skills(
    params: MarketFilterParams = Depends(),
    limit: int = Query(25, ge=1, le=100),
    skill_category: Optional[str] = Query(None, max_length=255, description="Lọc theo nhóm kỹ năng."),
    search: Optional[str] = Query(None, max_length=80, description="Tìm theo tên kỹ năng."),
    db: AsyncSession = Depends(get_db),
):
    if skill_category and skill_category not in SKILL_CATEGORY_VALUES:
        raise HTTPException(
            status_code=422,
            detail=f"skill_category không hợp lệ: {skill_category}",
        )
    return await get_skills_intelligence(
        db,
        params.to_filters(),
        limit=limit,
        skill_category=skill_category,
        search=search,
    )


@router.get("/roles", response_model=RolesResponse)
async def market_roles(
    params: MarketFilterParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    return await get_role_intelligence(db, params.to_filters())


@router.get("/geography", response_model=GeographyResponse)
async def market_geography(
    params: MarketFilterParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    return await get_geography_intelligence(db, params.to_filters())


@router.get("/employers", response_model=EmployersResponse)
async def market_employers(
    params: MarketFilterParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    return await get_employer_intelligence(db, params.to_filters())


@router.get("/insights", response_model=InsightsResponse)
async def market_insights(
    params: MarketFilterParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    return await get_insights(db, params.to_filters())
