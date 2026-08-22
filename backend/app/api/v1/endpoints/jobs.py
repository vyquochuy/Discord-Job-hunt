import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.job import (
    Job,
    JobLevelEnum,
    JobSkill,
    JobStatusEnum,
    RawJob,
    Skill,
    SkillAlias,
    WorkModeEnum,
)
from app.schemas.job import (
    JobDetailResponse,
    JobListResponse,
    JobResponse,
    SkillTaxonomyResponse,
)
from app.services.collectors.careerlink_adapter import CareerLinkJobCollector
from app.services.collectors.itviec_adapter import ITViecJobCollector
from app.services.collectors.mock_adapter import MockJobCollector
from app.services.collectors.remotive_adapter import RemotiveJobCollector
from app.services.collectors.topcv_adapter import TopCVJobCollector
from app.services.ingestion_pipeline import ingestion_pipeline

router = APIRouter()


@router.get("", response_model=JobListResponse)
async def list_jobs(
    keyword: Optional[str] = Query(None, description="Tìm kiếm theo tiêu đề, công ty hoặc mô tả"),
    work_mode: Optional[WorkModeEnum] = Query(None, description="Hình thức làm việc: ONSITE, HYBRID, REMOTE"),
    level: Optional[JobLevelEnum] = Query(None, description="Cấp bậc: INTERN, FRESHER, JUNIOR, MID, SENIOR, LEAD"),
    location: Optional[str] = Query(None, description="Địa điểm (ví dụ: 'Ho Chi Minh City', 'Hanoi')"),
    page: int = Query(1, ge=1, description="Số trang (bắt đầu từ 1)"),
    page_size: int = Query(20, ge=1, le=100, description="Số lượng job mỗi trang"),
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy danh sách các tin tuyển dụng đã chuẩn hóa (có hỗ trợ tìm kiếm và lọc).
    """
    query = select(Job).options(selectinload(Job.raw_job)).where(Job.status == JobStatusEnum.ACTIVE)


    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.where(
            or_(
                Job.title.ilike(pattern),
                Job.company_name.ilike(pattern),
                Job.normalized_title.ilike(pattern),
                Job.description.ilike(pattern),
            )
        )

    if work_mode:
        query = query.where(Job.work_mode == work_mode)

    if level and level != JobLevelEnum.UNKNOWN:
        query = query.where(Job.level == level)

    if location:
        query = query.where(Job.normalized_location.ilike(f"%{location.strip()}%"))

    # Đếm tổng số bản ghi
    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    # Phân trang và sắp xếp mới nhất
    offset = (page - 1) * page_size
    query = query.order_by(Job.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    jobs = result.scalars().all()

    return JobListResponse(
        items=[JobResponse.model_validate(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{job_id}", response_model=JobDetailResponse)
async def get_job_detail(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy chi tiết một tin tuyển dụng cùng các kỹ năng yêu cầu và thông tin dữ liệu thô.
    """
    stmt = (
        select(Job)
        .where(Job.id == job_id)
        .options(
            selectinload(Job.skills).selectinload(JobSkill.skill),
            selectinload(Job.raw_job),
        )
    )
    result = await db.execute(stmt)
    job = result.scalars().first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found",
        )

    return JobDetailResponse.model_validate(job)


@router.post("/collect")
async def trigger_collection(
    source: str = Query("mock", description="Nguồn thu thập: 'mock', 'remotive', 'itviec', 'careerlink', 'topcv'"),
    limit: int = Query(5, ge=1, le=50, description="Số lượng tin tối đa thu thập"),
    db: AsyncSession = Depends(get_db),
):
    """
    Kích hoạt thu thập và chuẩn hóa tin tuyển dụng thủ công theo yêu cầu.
    """
    collectors_map = {
        "mock": MockJobCollector(),
        "remotive": RemotiveJobCollector(),
        "itviec": ITViecJobCollector(),
        "careerlink": CareerLinkJobCollector(),
        "topcv": TopCVJobCollector(),
    }

    if source not in collectors_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid source '{source}'. Available sources: {list(collectors_map.keys())}",
        )

    collector = collectors_map[source]
    stats = await ingestion_pipeline.run(collector, db, limit=limit)

    return {
        "status": "success",
        "source": source,
        "report": {
            "total_fetched": stats.total_fetched,
            "created": stats.created,
            "unchanged": stats.unchanged,
            "duplicates_detected": stats.duplicates_detected,
            "errors": stats.errors,
        },
    }


@router.get("/taxonomy/skills", response_model=List[SkillTaxonomyResponse])
async def list_canonical_skills(
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy danh mục các kỹ năng chuẩn hóa (Canonical Skills) và từ đồng nghĩa.
    """
    stmt = select(Skill).options(selectinload(Skill.aliases)).order_by(Skill.canonical_name.asc())
    result = await db.execute(stmt)
    skills = result.scalars().all()
    return [SkillTaxonomyResponse.model_validate(s) for s in skills]
