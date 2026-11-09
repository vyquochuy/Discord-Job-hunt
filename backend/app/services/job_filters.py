"""Database-backed catalog of filter values present on active jobs."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job, JobStatusEnum, RawJob
from app.schemas.job import JobFilterOption, JobFiltersResponse

SOURCE_LABELS = {
    "itviec": "ITViec", "topcv": "TopCV", "saramin": "Saramin",
    "topdev": "TopDev (legacy)", "careerlink": "CareerLink",
    "remotive": "Remotive", "itnavi": "ITNavi", "growupwork": "GrowUpWork",
    "vietnamworks": "VietnamWorks", "upwork": "Upwork",
    "manual": "Nhập thủ công", "mock": "Dữ liệu mẫu",
}
LEVEL_LABELS = {"MID": "Mid-level", "UNKNOWN": "Chưa xác định"}


async def get_job_filters(db: AsyncSession) -> JobFiltersResponse:
    catalog = {}
    for name, column in (
        ("sources", RawJob.source), ("levels", Job.level),
        ("work_modes", Job.work_mode), ("locations", Job.normalized_location),
    ):
        query = (
            select(column, func.count(Job.id))
            .select_from(Job).join(Job.raw_job)
            .where(Job.status == JobStatusEnum.ACTIVE, column.is_not(None), column != "")
            .group_by(column).order_by(column)
        )
        options = []
        for value, count in (await db.execute(query)).all():
            value = value.value if hasattr(value, "value") else value
            label = value
            if name == "sources":
                label = SOURCE_LABELS.get(value, value)
            elif name == "levels":
                label = LEVEL_LABELS.get(value, value.title())
            elif name == "work_modes":
                label = value.title()
            options.append(JobFilterOption(value=value, label=label, count=count))
        catalog[name] = options
    return JobFiltersResponse(**catalog)
