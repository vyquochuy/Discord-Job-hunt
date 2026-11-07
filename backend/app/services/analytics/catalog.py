"""Filter catalog endpoint: values actually present in the database."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Dict

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.analytics.common import distribution_items
from app.services.analytics.filters import (
    MarketFilters,
    date_bounds,
    load_job_facts,
    load_skill_links,
)
from app.services.analytics.taxonomy import (
    CATEGORY_LABELS,
    CATEGORY_ORDER,
    LEVEL_LABELS,
    LEVEL_ORDER,
    REGION_LABELS,
    REGION_ORDER,
    WORK_MODE_LABELS,
)


async def get_filter_catalog(db: AsyncSession) -> Dict[str, object]:
    facts = await load_job_facts(db, MarketFilters())
    if not facts:
        # Fall back to expired records so the UI still has something to filter
        # when every current listing has expired.
        facts = await load_job_facts(db, MarketFilters(include_expired=True))

    total = len(facts)
    links = await load_skill_links(db, facts)
    start, end = date_bounds(facts)

    skill_counts = Counter(link.skill for link in links)
    skills = [
        {"value": skill, "label": skill, "jobs": int(count)}
        for skill, count in skill_counts.most_common(50)
    ]

    return {
        "date_range": {
            "min": start.isoformat() if start else None,
            "max": end.isoformat() if end else None,
        },
        "levels": distribution_items(
            (fact.level for fact in facts),
            LEVEL_LABELS,
            total=total,
            order=LEVEL_ORDER,
        ),
        "categories": distribution_items(
            (fact.category for fact in facts),
            CATEGORY_LABELS,
            total=total,
            order=CATEGORY_ORDER,
        ),
        "locations": distribution_items(
            (fact.location for fact in facts if fact.location),
            {fact.location: fact.location for fact in facts if fact.location},
            total=total,
            limit=60,
        ),
        "regions": distribution_items(
            (fact.region for fact in facts),
            REGION_LABELS,
            total=total,
            order=REGION_ORDER,
        ),
        "sources": distribution_items(
            (fact.source for fact in facts),
            {fact.source: fact.source for fact in facts},
            total=total,
        ),
        "work_modes": distribution_items(
            (fact.work_mode for fact in facts),
            WORK_MODE_LABELS,
            total=total,
            order=["ONSITE", "HYBRID", "REMOTE"],
        ),
        "skills": skills,
        "total_jobs": total,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
