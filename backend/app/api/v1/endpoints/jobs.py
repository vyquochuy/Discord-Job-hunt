import uuid
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.limiter import limiter
from app.core.security import get_authenticated_user_or_internal, get_current_user_optional
from app.api.v1.endpoints.system import verify_admin_access
from app.models.user import User
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
    ManualJobIngestRequest,
    ManualJobIngestResponse,
    SkillTaxonomyResponse,
)
from app.schemas.saved_job import SavedJobCreate, SavedJobResponse
from app.services.collectors.careerlink_adapter import CareerLinkJobCollector
from app.services.collectors.growupwork_adapter import GrowUpWorkJobCollector
from app.services.collectors.itnavi_adapter import ITNaviJobCollector
from app.services.collectors.itviec_adapter import ITViecJobCollector
from app.services.collectors.mock_adapter import MockJobCollector
from app.services.collectors.remotive_adapter import RemotiveJobCollector
from app.services.collectors.topcv_adapter import TopCVJobCollector
from app.services.collectors.topdev_adapter import TopDevJobCollector
from app.services.collectors.upwork_adapter import UpworkJobCollector
from app.services.collectors.vietnamworks_adapter import VietnamWorksJobCollector
from app.services.ingestion_pipeline import ingestion_pipeline
from app.services.manual_ingestion_service import manual_ingestion_service

router = APIRouter()


@router.get("", response_model=JobListResponse)
async def list_jobs(
    keyword: Optional[str] = Query(None, description="Tìm kiếm theo tiêu đề, công ty hoặc mô tả"),
    work_mode: Optional[WorkModeEnum] = Query(None, description="Hình thức làm việc: ONSITE, HYBRID, REMOTE"),
    level: Optional[JobLevelEnum] = Query(None, description="Cấp bậc: INTERN, FRESHER, JUNIOR, MID, SENIOR, LEAD"),
    location: Optional[str] = Query(None, description="Địa điểm (ví dụ: 'Ho Chi Minh City', 'Hanoi')"),
    source: Optional[str] = Query(None, description="Nguồn tin tuyển dụng: topcv, itviec, careerlink, remotive, mock"),
    page: int = Query(1, ge=1, description="Số trang (bắt đầu từ 1)"),
    page_size: int = Query(20, ge=1, le=100, description="Số lượng job mỗi trang"),
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy danh sách các tin tuyển dụng đã chuẩn hóa (có hỗ trợ tìm kiếm và lọc).
    """
    query = select(Job).options(selectinload(Job.raw_job)).where(Job.status == JobStatusEnum.ACTIVE)

    if source:
        src = source.strip().lower()
        if src == "other":
            query = query.join(Job.raw_job).where(
                ~RawJob.source.in_([
                    "topcv", "itviec", "careerlink", "remotive",
                    "topdev", "itnavi", "growupwork", "vietnamworks", "upwork",
                    "mock", "manual"
                ])
            )
        else:
            query = query.join(Job.raw_job).where(RawJob.source == src)


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


@router.get("/saved", response_model=List[dict])
async def list_saved_jobs(
    current_user: User = Depends(get_authenticated_user_or_internal),
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy danh sách các tin tuyển dụng đã lưu (Saved / Bookmarked) của người dùng đang đăng nhập.
    """
    from app.models.saved_job import SavedJob

    query = (
        select(SavedJob)
        .options(selectinload(SavedJob.job).selectinload(Job.raw_job))
        .where(SavedJob.user_id == current_user.id)
        .order_by(SavedJob.created_at.desc())
    )
    result = await db.execute(query)
    saved_list = result.scalars().all()

    items = []
    for s in saved_list:
        job_data = JobResponse.model_validate(s.job).model_dump() if s.job else None
        items.append({
            "id": s.id,
            "user_id": s.user_id,
            "job_id": s.job_id,
            "notes": s.notes,
            "created_at": s.created_at,
            "job": job_data,
        })
    return items


@router.post("/{job_id}/save")
async def save_job(
    job_id: uuid.UUID,
    payload: Optional[SavedJobCreate] = None,
    current_user: User = Depends(get_authenticated_user_or_internal),
    db: AsyncSession = Depends(get_db),
):
    """
    Lưu / Bookmark một tin tuyển dụng vào danh sách theo dõi của người dùng.
    """
    from app.models.saved_job import SavedJob

    # Kiểm tra job có tồn tại không
    job_stmt = select(Job).where(Job.id == job_id)
    job_res = await db.execute(job_stmt)
    job = job_res.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found",
        )

    user_id = current_user.id

    # Kiểm tra xem đã lưu chưa
    saved_stmt = select(SavedJob).where(
        SavedJob.user_id == user_id,
        SavedJob.job_id == job_id,
    )
    saved_res = await db.execute(saved_stmt)
    existing_saved = saved_res.scalar_one_or_none()

    if existing_saved:
        if payload and payload.notes is not None:
            existing_saved.notes = payload.notes
            await db.commit()
        return {"status": "already_saved", "saved_job_id": existing_saved.id}

    notes = payload.notes if payload else None
    saved_item = SavedJob(
        id=uuid.uuid4(),
        user_id=user_id,
        job_id=job_id,
        notes=notes,
    )
    db.add(saved_item)
    await db.commit()

    return {"status": "saved", "saved_job_id": saved_item.id}


@router.delete("/{job_id}/save")
async def unsave_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_authenticated_user_or_internal),
    db: AsyncSession = Depends(get_db),
):
    """
    Hủy lưu (Unsave / Remove Bookmark) một tin tuyển dụng.
    """
    from app.models.saved_job import SavedJob

    user_id = current_user.id

    saved_stmt = select(SavedJob).where(
        SavedJob.user_id == user_id,
        SavedJob.job_id == job_id,
    )
    saved_res = await db.execute(saved_stmt)
    saved_item = saved_res.scalar_one_or_none()

    if not saved_item:
        return {"status": "not_found"}

    await db.delete(saved_item)
    await db.commit()

    return {"status": "unsaved"}
 
 
@router.post("/ingest-manual", response_model=ManualJobIngestResponse)
@limiter.limit("5/minute")
async def ingest_manual_job(
    request: Request,
    payload: ManualJobIngestRequest,
    db: AsyncSession = Depends(get_db),
    _user: Any = Depends(get_authenticated_user_or_internal),
):
    """
    Nạp tin tuyển dụng thủ công từ Văn bản thô (Facebook/Zalo/Email) hoặc URL trực tiếp.
    Chuẩn hóa tự động, kiểm tra trùng lặp 3 tầng, sinh embedding và tính điểm phù hợp 7 tín hiệu tức thì.
    """
    return await manual_ingestion_service.ingest(db=db, payload=payload)
 
 
@router.get("/{job_id}", response_model=JobDetailResponse)
async def get_job_detail(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy chi tiết một tin tuyển dụng cùng các kỹ năng yêu cầu và thông tin dữ liệu thô (Công khai).
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
    _auth: bool = Depends(verify_admin_access),
):
    """
    Kích hoạt thu thập và chuẩn hóa tin tuyển dụng thủ công theo yêu cầu (Yêu cầu quyền Quản trị).
    """
    collectors_map = {
        "mock": MockJobCollector(),
        "remotive": RemotiveJobCollector(),
        "itviec": ITViecJobCollector(),
        "careerlink": CareerLinkJobCollector(),
        "topcv": TopCVJobCollector(),
        "topdev": TopDevJobCollector(),
        "itnavi": ITNaviJobCollector(),
        "growupwork": GrowUpWorkJobCollector(),
        "vietnamworks": VietnamWorksJobCollector(),
        "upwork": UpworkJobCollector(),
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


@router.post("/daily-batch")
async def trigger_daily_batch(
    limit_per_source: int = Query(50, ge=1, le=500, description="Số lượng tin tối đa mỗi nguồn (hỗ trợ quét sâu 1 tháng lên đến 500 tin/nguồn)"),
    db: AsyncSession = Depends(get_db),
    _auth: bool = Depends(verify_admin_access),
):
    """
    Kích hoạt toàn bộ chu kỳ Daily Autonomous Job Scan & Intelligence (Yêu cầu quyền Quản trị):
    Sync Context -> Sync Taxonomy -> Ingest Jobs (0 LLM Cost) -> Match & Score -> Rank Top Recommendations.
    """
    from app.services.daily_runner import daily_batch_runner

    summary = await daily_batch_runner.run_daily_batch(session=db, limit_per_source=limit_per_source)
    return summary


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
