from app.services.analytics.stats import native_midpoint
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.job import Job, JobSkill, JobStatusEnum, RawJob, Skill


async def get_market_analytics(db: AsyncSession) -> dict:
    active = await db.scalar(select(func.count(Job.id)).where(Job.status == JobStatusEnum.ACTIVE)) or 0
    expired = await db.scalar(select(func.count(Job.id)).where(Job.status == JobStatusEnum.EXPIRED)) or 0

    source_rows = await db.execute(
        select(RawJob.source, func.count(Job.id)).join(Job, Job.raw_job_id == RawJob.id)
        .where(Job.status == JobStatusEnum.ACTIVE).group_by(RawJob.source)
    )
    sources = [{"source": source, "jobs": count} for source, count in source_rows]

    skill_rows = await db.execute(
        select(Skill.canonical_name, func.count(JobSkill.id))
        .join(JobSkill, JobSkill.skill_id == Skill.id)
        .join(Job, Job.id == JobSkill.job_id)
        .where(Job.status == JobStatusEnum.ACTIVE)
        .group_by(Skill.canonical_name).order_by(func.count(JobSkill.id).desc()).limit(20)
    )
    top_skills = [{"skill": skill, "jobs": count} for skill, count in skill_rows]

    # Legacy shape keeps average_max semantics; only valid native VND ranges
    # participate, never a mixed USD/VND aggregate.
    salary = await db.execute(
        select(Job.min_salary, Job.max_salary)
        .where(
            Job.status == JobStatusEnum.ACTIVE,
            func.upper(func.trim(Job.salary_currency)) == "VND",
            Job.max_salary.is_not(None),
        )
    )
    valid = [(low, high) for low, high in salary.all() if native_midpoint(low, high) is not None]
    lows = [low for low, _ in valid if low is not None]
    highs = [high for _, high in valid]
    minimum = min(lows) if lows else None
    average = sum(highs) / len(highs) if highs else None
    maximum = max(highs) if highs else None
    return {
        "total_active_jobs": active,
        "total_expired_jobs": expired,
        "sources": sources,
        "top_skills": top_skills,
        "salary": {"min": minimum, "average_max": average, "max": maximum},
    }
