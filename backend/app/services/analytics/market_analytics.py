from collections import Counter
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

    salary = await db.execute(
        select(func.min(Job.min_salary), func.avg(Job.max_salary), func.max(Job.max_salary))
        .where(Job.status == JobStatusEnum.ACTIVE, Job.max_salary.is_not(None))
    )
    minimum, average, maximum = salary.one()
    return {
        "total_active_jobs": active,
        "total_expired_jobs": expired,
        "sources": sources,
        "top_skills": top_skills,
        "salary": {"min": minimum, "average_max": average, "max": maximum},
    }
