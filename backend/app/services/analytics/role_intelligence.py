"""Role Intelligence tab aggregates."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import timedelta
from typing import Dict, List, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.analytics.common import salary_summary
from app.services.analytics.filters import (
    JobFact,
    MarketFilters,
    load_job_facts,
    resolve_range,
)
from app.services.analytics.stats import market_meta, share, status_for
from app.services.analytics.taxonomy import (
    CATEGORY_LABELS,
    derive_category,
)


def summarize_roles(
    facts: Sequence[JobFact], filters: MarketFilters
) -> Dict[str, object]:
    total = len(facts)
    title_groups: Dict[str, List[JobFact]] = defaultdict(list)
    family_groups: Dict[str, List[JobFact]] = defaultdict(list)
    category_groups: Dict[str, List[JobFact]] = defaultdict(list)
    for fact in facts:
        title_groups[fact.normalized_title].append(fact)
        family_groups[fact.role_family].append(fact)
        category_groups[fact.category].append(fact)

    top_titles: List[Dict[str, object]] = []
    for title, group in sorted(
        title_groups.items(), key=lambda item: len(item[1]), reverse=True
    )[:20]:
        salary = salary_summary(group)
        level_mix = Counter(fact.level for fact in group)
        top_titles.append(
            {
                "title": title,
                "jobs": len(group),
                "share": share(len(group), total),
                "level_mix": {key: int(value) for key, value in level_mix.items()},
                "median_salary_vnd": salary.get("median"),
                "salary_sample": salary.get("sample_size", 0),
                "category": derive_category(title),
            }
        )

    by_category: List[Dict[str, object]] = []
    for category, group in sorted(
        category_groups.items(), key=lambda item: len(item[1]), reverse=True
    ):
        salary = salary_summary(group)
        title_counter = Counter(fact.normalized_title for fact in group)
        by_category.append(
            {
                "category": category,
                "label": CATEGORY_LABELS.get(category, category),
                "jobs": len(group),
                "share": share(len(group), total),
                "top_titles": [title for title, _ in title_counter.most_common(5)],
                "median_salary_vnd": salary.get("median"),
                "salary_sample": salary.get("sample_size", 0),
            }
        )

    role_families: List[Dict[str, object]] = []
    for family, group in sorted(
        family_groups.items(), key=lambda item: len(item[1]), reverse=True
    )[:20]:
        title_counter = Counter(fact.normalized_title for fact in group)
        role_families.append(
            {
                "family": family,
                "jobs": len(group),
                "share": share(len(group), total),
                "examples": [title for title, _ in title_counter.most_common(3)],
            }
        )

    title_level_matrix: List[Dict[str, object]] = []
    for title, group in sorted(
        title_groups.items(), key=lambda item: len(item[1]), reverse=True
    )[:15]:
        levels = Counter(fact.level for fact in group)
        title_level_matrix.append(
            {
                "title": title,
                "total": len(group),
                "levels": {key: int(value) for key, value in levels.items()},
            }
        )

    # Emerging roles: same two-half comparison used by the skills tab.
    start, end = resolve_range(facts, filters)
    if start is None or end is None or (end - start).days + 1 < 21:
        emerging: Dict[str, object] = {
            "available": False,
            "reason": "Cần khoảng thời gian ít nhất 21 ngày để so sánh nửa đầu và nửa cuối.",
            "items": [],
        }
    else:
        span_days = (end - start).days + 1
        midpoint = start + timedelta(days=span_days // 2)
        earlier = [fact for fact in facts if fact.posted_date and fact.posted_date < midpoint]
        recent = [fact for fact in facts if fact.posted_date and fact.posted_date >= midpoint]
        earlier_counts = Counter(fact.normalized_title for fact in earlier)
        recent_counts = Counter(fact.normalized_title for fact in recent)
        items: List[Dict[str, object]] = []
        if earlier and recent:
            for title, recent_count in recent_counts.items():
                if recent_count < 3:
                    continue
                earlier_count = earlier_counts.get(title, 0)
                recent_share = recent_count / len(recent)
                earlier_share = earlier_count / len(earlier)
                delta = recent_share - earlier_share
                if delta <= 0:
                    continue
                items.append(
                    {
                        "title": title,
                        "recent_jobs": int(recent_count),
                        "earlier_jobs": int(earlier_count),
                        "recent_share": round(recent_share, 4),
                        "earlier_share": round(earlier_share, 4),
                        "delta": round(delta, 4),
                    }
                )
        items.sort(key=lambda item: item["delta"], reverse=True)
        emerging = {
            "available": bool(earlier and recent),
            "reason": None if earlier and recent else "Một trong hai nửa thời gian không có tin có ngày đăng.",
            "midpoint": midpoint.isoformat(),
            "items": items[:8],
        }

    notes: List[str] = []
    if total < 30:
        notes.append(f"Mẫu vị trí nhỏ (N={total}); diễn giải thận trọng.")
    if total and share(sum(1 for fact in facts if fact.posted_date is None), total) > 0:
        notes.append("Một số tin thiếu posted_at nên không tham gia so sánh hai nửa thời gian.")
    if not emerging["available"]:
        notes.append(str(emerging["reason"]))

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
        "top_titles": top_titles,
        "by_category": by_category,
        "role_families": role_families,
        "title_level_matrix": title_level_matrix,
        "emerging": emerging,
    }


async def get_role_intelligence(
    db: AsyncSession, filters: MarketFilters
) -> Dict[str, object]:
    facts = await load_job_facts(db, filters)
    return summarize_roles(facts, filters)
