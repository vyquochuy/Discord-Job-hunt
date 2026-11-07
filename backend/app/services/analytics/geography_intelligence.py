"""Geographic Intelligence tab aggregates."""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, List, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.analytics.common import salary_summary
from app.services.analytics.filters import (
    JobFact,
    MarketFilters,
    load_job_facts,
)
from app.services.analytics.stats import market_meta, share, status_for
from app.services.analytics.taxonomy import (
    CATEGORY_LABELS,
    REGION_LABELS,
    REGION_ORDER,
)


def summarize_geography(
    facts: Sequence[JobFact], filters: MarketFilters
) -> Dict[str, object]:
    total = len(facts)
    region_groups: Dict[str, List[JobFact]] = defaultdict(list)
    city_groups: Dict[str, List[JobFact]] = defaultdict(list)
    for fact in facts:
        region_groups[fact.region].append(fact)
        if fact.location:
            city_groups[fact.location].append(fact)

    regions: List[Dict[str, object]] = []
    for region in REGION_ORDER:
        group = region_groups.get(region, [])
        if not group:
            continue
        salary = salary_summary(group)
        category_counter = Counter(fact.category for fact in group)
        regions.append(
            {
                "region": region,
                "label": REGION_LABELS.get(region, region),
                "jobs": len(group),
                "share": share(len(group), total),
                "companies": len(
                    {fact.normalized_company for fact in group if fact.normalized_company}
                ),
                "median_salary_vnd": salary.get("median"),
                "salary_sample": salary.get("sample_size", 0),
                "top_categories": [
                    CATEGORY_LABELS.get(category, category)
                    for category, _ in category_counter.most_common(3)
                ],
            }
        )

    cities: List[Dict[str, object]] = []
    for location, group in sorted(
        city_groups.items(), key=lambda item: len(item[1]), reverse=True
    )[:25]:
        salary = salary_summary(group)
        cities.append(
            {
                "location": location,
                "jobs": len(group),
                "share": share(len(group), total),
                "companies": len(
                    {fact.normalized_company for fact in group if fact.normalized_company}
                ),
                "median_salary_vnd": salary.get("median"),
                "salary_sample": salary.get("sample_size", 0),
            }
        )

    top_categories = [
        category
        for category, _ in Counter(fact.category for fact in facts).most_common(6)
    ]
    by_category: List[Dict[str, object]] = []
    for category in top_categories:
        category_facts = [fact for fact in facts if fact.category == category]
        region_counts = Counter(fact.region for fact in category_facts)
        by_category.append(
            {
                "category": category,
                "label": CATEGORY_LABELS.get(category, category),
                "total": len(category_facts),
                "regions": {
                    region: int(region_counts.get(region, 0))
                    for region in REGION_ORDER
                },
            }
        )

    work_modes = Counter(fact.work_mode for fact in facts)
    remote_share = {
        "remote": work_modes.get("REMOTE", 0),
        "hybrid": work_modes.get("HYBRID", 0),
        "onsite": work_modes.get("ONSITE", 0),
        "remote_ratio": share(work_modes.get("REMOTE", 0), total),
        "flexible_ratio": share(
            work_modes.get("REMOTE", 0) + work_modes.get("HYBRID", 0), total
        ),
    }

    salary_by_region: List[Dict[str, object]] = []
    for region in REGION_ORDER:
        group = region_groups.get(region, [])
        salary = salary_summary(group)
        if salary.get("sample_size", 0) == 0:
            continue
        salary.update(
            {
                "key": region,
                "label": REGION_LABELS.get(region, region),
                "jobs": len(group),
                "status": status_for(int(salary["sample_size"]), min_sample=3),
            }
        )
        salary_by_region.append(salary)
    salary_by_region.sort(key=lambda item: item.get("median") or 0, reverse=True)

    notes: List[str] = []
    missing_location = sum(1 for fact in facts if not fact.location)
    if missing_location:
        notes.append(
            f"{missing_location}/{total} tin thiếu địa điểm; không được gán vào vùng nào."
        )
    notes.append(
        "Vùng được suy ra từ normalized_location; các địa danh không khớp sẽ rơi vào "
        "'Tỉnh / thành khác' hoặc 'Quốc tế'."
    )
    if total < 30:
        notes.append(f"Mẫu địa lý nhỏ (N={total}); diễn giải thận trọng.")

    meta = market_meta(
        filters.as_dict(),
        total_jobs=total,
        sample_size=total,
        coverage=1.0,
        status=status_for(total),
        notes=notes,
    )

    return {
        "meta": meta,
        "regions": regions,
        "cities": cities,
        "by_category": by_category,
        "remote_share": remote_share,
        "salary_by_region": salary_by_region,
    }


async def get_geography_intelligence(
    db: AsyncSession, filters: MarketFilters
) -> Dict[str, object]:
    facts = await load_job_facts(db, filters)
    return summarize_geography(facts, filters)
