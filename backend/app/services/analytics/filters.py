"""
Shared market filter model and compact job fact loader.

The loader intentionally selects only the columns the analytics modules need.
Derived dimensions (category, region, role family) are computed in Python so
that every endpoint applies exactly the same deterministic rules regardless of
the SQL dialect (PostgreSQL in production, SQLite in tests).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta, timezone
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import (
    Job,
    JobLevelEnum,
    JobSkill,
    JobStatusEnum,
    RawJob,
    Skill,
    WorkModeEnum,
)
from app.services.analytics.taxonomy import (
    derive_category,
    derive_region,
    derive_role_family,
)


MARKET_SOURCES = (
    "itviec", "topcv", "saramin", "topdev",
    "vietnamworks", "careerlink", "itnavi", "growupwork",
)


def market_source_predicate():
    """Keep supported sources, excluding historical synthetic fallback records."""
    return and_(
        RawJob.source.in_(MARKET_SOURCES),
        or_(
            RawJob.source_job_id.is_(None),
            ~RawJob.source_job_id.startswith("growupwork-curated-"),
        ),
    )


@dataclass(frozen=True, slots=True)
class MarketFilters:
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    category: Optional[str] = None
    level: Optional[str] = None
    location: Optional[str] = None
    region: Optional[str] = None
    source: Optional[str] = None
    work_mode: Optional[str] = None
    skill: Optional[str] = None
    company: Optional[str] = None
    include_expired: bool = False

    def as_dict(self) -> Dict[str, object]:
        return {
            "date_from": self.date_from.isoformat() if self.date_from else None,
            "date_to": self.date_to.isoformat() if self.date_to else None,
            "category": self.category,
            "level": self.level,
            "location": self.location,
            "region": self.region,
            "source": self.source,
            "work_mode": self.work_mode,
            "skill": self.skill,
            "company": self.company,
            "include_expired": self.include_expired,
        }

    def with_dates(self, date_from: Optional[date], date_to: Optional[date]) -> "MarketFilters":
        return replace(self, date_from=date_from, date_to=date_to)

    @property
    def has_date_filter(self) -> bool:
        return self.date_from is not None or self.date_to is not None


@dataclass(frozen=True, slots=True)
class JobFact:
    id: uuid.UUID
    title: str
    normalized_title: str
    category: str
    company: str
    normalized_company: str
    location: Optional[str]
    region: str
    level: str
    work_mode: str
    posted_at: Optional[datetime]
    posted_date: Optional[date]
    min_salary: Optional[float]
    max_salary: Optional[float]
    salary_currency: Optional[str]
    is_salary_negotiable: bool
    status: str
    source: str
    role_family: str

    @property
    def has_salary_amount(self) -> bool:
        return self.min_salary is not None or self.max_salary is not None


@dataclass(frozen=True, slots=True)
class SkillLink:
    job_id: uuid.UUID
    skill: str
    category: str


def _enum_value(value: object) -> str:
    if hasattr(value, "value"):
        return str(getattr(value, "value"))
    return str(value)


def _utc_start(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=timezone.utc)


def _utc_end_exclusive(day: date) -> datetime:
    return datetime.combine(day + timedelta(days=1), time.min, tzinfo=timezone.utc)


def _chunked(items: Sequence[uuid.UUID], size: int = 900) -> Iterable[Sequence[uuid.UUID]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def build_job_query(filters: MarketFilters) -> Select:
    """Build the filtered SELECT used by `load_job_facts`."""
    statement = (
        select(
            Job.id,
            Job.title,
            Job.normalized_title,
            Job.company_name,
            Job.normalized_company,
            Job.location,
            Job.normalized_location,
            Job.level,
            Job.work_mode,
            Job.posted_at,
            Job.min_salary,
            Job.max_salary,
            Job.salary_currency,
            Job.is_salary_negotiable,
            Job.status,
            RawJob.source,
        )
        .join(RawJob, RawJob.id == Job.raw_job_id)
        .where(market_source_predicate())
    )

    if filters.include_expired:
        statement = statement.where(
            Job.status.in_([JobStatusEnum.ACTIVE, JobStatusEnum.EXPIRED])
        )
    else:
        statement = statement.where(Job.status == JobStatusEnum.ACTIVE)

    if filters.date_from is not None:
        statement = statement.where(Job.posted_at >= _utc_start(filters.date_from))
    if filters.date_to is not None:
        statement = statement.where(Job.posted_at < _utc_end_exclusive(filters.date_to))

    if filters.level:
        statement = statement.where(Job.level == JobLevelEnum(filters.level))
    if filters.location:
        statement = statement.where(Job.normalized_location == filters.location)
    if filters.source:
        statement = statement.where(RawJob.source == filters.source)
    if filters.work_mode:
        statement = statement.where(Job.work_mode == WorkModeEnum(filters.work_mode))
    if filters.company:
        statement = statement.where(Job.normalized_company == filters.company)
    if filters.skill:
        statement = (
            statement.join(JobSkill, JobSkill.job_id == Job.id)
            .join(Skill, Skill.id == JobSkill.skill_id)
            .where(Skill.canonical_name == filters.skill)
        )

    return statement


async def load_job_facts(
    db: AsyncSession, filters: MarketFilters
) -> List[JobFact]:
    rows = (await db.execute(build_job_query(filters))).all()
    facts: List[JobFact] = []
    for row in rows:
        posted_at = row.posted_at
        posted_date = posted_at.date() if posted_at is not None else None
        normalized_title = row.normalized_title or row.title or ""
        facts.append(
            JobFact(
                id=row.id,
                title=row.title or "",
                normalized_title=normalized_title,
                category=derive_category(normalized_title),
                company=row.company_name or "",
                normalized_company=row.normalized_company or "",
                location=row.normalized_location or row.location,
                region=derive_region(row.normalized_location or row.location),
                level=_enum_value(row.level),
                work_mode=_enum_value(row.work_mode),
                posted_at=posted_at,
                posted_date=posted_date,
                min_salary=row.min_salary,
                max_salary=row.max_salary,
                salary_currency=(row.salary_currency or "").upper() or None,
                is_salary_negotiable=bool(row.is_salary_negotiable),
                status=_enum_value(row.status),
                source=row.source or "unknown",
                role_family=derive_role_family(normalized_title),
            )
        )

    # Derived filters must be applied after the SQL pre-filter because category
    # and region are not stored columns.
    if filters.category:
        facts = [fact for fact in facts if fact.category == filters.category]
    if filters.region:
        facts = [fact for fact in facts if fact.region == filters.region]

    return facts


async def load_skill_links(
    db: AsyncSession, facts: Sequence[JobFact]
) -> List[SkillLink]:
    if not facts:
        return []
    ids = [fact.id for fact in facts]
    links: List[SkillLink] = []
    for chunk in _chunked(ids):
        statement = (
            select(JobSkill.job_id, Skill.canonical_name, Skill.category)
            .join(Skill, Skill.id == JobSkill.skill_id)
            .where(JobSkill.job_id.in_(chunk))
        )
        for job_id, canonical_name, category in (await db.execute(statement)).all():
            links.append(
                SkillLink(
                    job_id=job_id,
                    skill=canonical_name,
                    category=_enum_value(category),
                )
            )
    return links


def date_bounds(facts: Sequence[JobFact]) -> Tuple[Optional[date], Optional[date]]:
    dates = [fact.posted_date for fact in facts if fact.posted_date is not None]
    if not dates:
        return None, None
    return min(dates), max(dates)


def resolve_range(
    facts: Sequence[JobFact], filters: MarketFilters
) -> Tuple[Optional[date], Optional[date]]:
    inferred_start, inferred_end = date_bounds(facts)
    start = filters.date_from or inferred_start
    end = filters.date_to or inferred_end
    return start, end


def previous_period(start: date, end: date) -> Tuple[date, date]:
    length = (end - start).days + 1
    previous_end = start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=max(length - 1, 0))
    return previous_start, previous_end


def with_previous_period(
    filters: MarketFilters, start: date, end: date
) -> MarketFilters:
    previous_start, previous_end = previous_period(start, end)
    return filters.with_dates(previous_start, previous_end)
