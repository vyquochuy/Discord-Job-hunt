"""Overview tab aggregates."""
from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from typing import Dict, List, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.analytics.buckets import daily_counts, detect_bulk_spikes, spike_caveats
from app.services.analytics.common import distribution_items
from app.services.analytics.filters import (
    JobFact,
    MarketFilters,
    SkillLink,
    date_bounds,
    load_job_facts,
    load_skill_links,
)
from app.services.analytics.stats import market_meta, salary_vnd, share, status_for
from app.services.analytics.taxonomy import (
    CATEGORY_LABELS,
    LEVEL_LABELS,
    LEVEL_ORDER,
    REGION_LABELS,
    REGION_ORDER,
    WORK_MODE_LABELS,
)


def _recent_window(
    dates: Sequence[date], reference: date, start_offset: int, end_offset: int
) -> int:
    start = reference - timedelta(days=start_offset)
    end = reference - timedelta(days=end_offset)
    return sum(1 for day in dates if start <= day <= end)


def summarize_overview(
    facts: Sequence[JobFact],
    links: Sequence[SkillLink],
    filters: MarketFilters,
) -> Dict[str, object]:
    total = len(facts)
    dates = [fact.posted_date for fact in facts if fact.posted_date is not None]
    inferred_start, inferred_end = date_bounds(facts)
    reference = inferred_end or date.today()

    last_7 = _recent_window(dates, reference, 6, 0)
    previous_7 = _recent_window(dates, reference, 13, 7)
    last_30 = _recent_window(dates, reference, 29, 0)
    change_pct = (
        round((last_7 - previous_7) / previous_7 * 100, 1) if previous_7 else None
    )

    levels = Counter(fact.level for fact in facts)
    sources = Counter(fact.source for fact in facts)

    with_salary = sum(
        1
        for fact in facts
        if salary_vnd(fact.min_salary, fact.max_salary, fact.salary_currency) is not None
    )
    negotiable = sum(1 for fact in facts if fact.is_salary_negotiable)
    missing_level = levels.get("UNKNOWN", 0)
    missing_location = sum(1 for fact in facts if not fact.location)
    missing_posted = total - len(dates)

    spikes = detect_bulk_spikes(dates)
    notes: List[str] = [
        "Mẫu tin thu thập không bảo đảm đại diện thị trường IT Việt Nam; số 0 chỉ là không "
        "có tin quan sát được. Chỉ số gần đây tính theo ngày cuối có dữ liệu, không phải hôm nay."
    ]
    if not filters.include_expired:
        notes.append("Chỉ xét tin hiện ACTIVE nên phân tích theo thời gian có thiên lệch sống sót.")
    if missing_posted:
        notes.append(
            f"{missing_posted}/{total} tin không có posted_at nên không tham gia phân tích xu hướng."
        )
    if with_salary and total and with_salary / total < 0.25:
        notes.append(
            f"Chỉ {with_salary}/{total} tin ({share(with_salary, total) * 100:.1f}%) "
            "có dữ liệu lương; các chỉ số lương không đại diện toàn thị trường."
        )
    notes.extend(spike_caveats(spikes))
    if inferred_start and inferred_end:
        notes.append(
            "Khoảng dữ liệu thực tế: "
            f"{inferred_start.isoformat()} → {inferred_end.isoformat()}."
        )

    sparkline: List[Dict[str, object]] = []
    if dates:
        counts = daily_counts(dates)
        for offset in range(29, -1, -1):
            day = reference - timedelta(days=offset)
            sparkline.append(
                {
                    "bucket": day.isoformat(),
                    "label": day.strftime("%d/%m"),
                    "jobs": counts.get(day, 0),
                }
            )

    status = status_for(total)
    meta = market_meta(
        filters.as_dict(),
        total_jobs=total,
        sample_size=total,
        coverage=1.0,
        status=status,
        notes=notes,
    )

    return {
        "meta": meta,
        "totals": {
            "jobs": total,
            "active": sum(1 for fact in facts if fact.status == "ACTIVE"),
            "expired": sum(1 for fact in facts if fact.status == "EXPIRED"),
            "companies": len({fact.normalized_company for fact in facts if fact.normalized_company}),
            "locations": len({fact.location for fact in facts if fact.location}),
            "skills": len({link.skill for link in links}),
            "sources": len(sources),
        },
        "recent": {
            "reference_date": reference.isoformat(),
            "last_7_days": last_7,
            "previous_7_days": previous_7,
            "change_pct": change_pct,
            "last_30_days": last_30,
        },
        "distributions": {
            "categories": distribution_items(
                (fact.category for fact in facts),
                CATEGORY_LABELS,
                total=total,
            ),
            "levels": distribution_items(
                (fact.level for fact in facts),
                LEVEL_LABELS,
                total=total,
                order=LEVEL_ORDER,
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
        },
        "data_quality": {
            "salary_coverage": {
                "with_salary": with_salary,
                "total": total,
                "ratio": share(with_salary, total),
                "negotiable": negotiable,
            },
            "missing_level": missing_level,
            "missing_location": missing_location,
            "missing_posted_at": missing_posted,
            "date_range": {
                "min": inferred_start.isoformat() if inferred_start else None,
                "max": inferred_end.isoformat() if inferred_end else None,
                "days": (
                    (inferred_end - inferred_start).days + 1
                    if inferred_start and inferred_end
                    else 0
                ),
            },
            "bulk_spikes": spikes,
        },
        "sparkline": sparkline,
    }


async def get_overview(
    db: AsyncSession, filters: MarketFilters
) -> Dict[str, object]:
    facts = await load_job_facts(db, filters)
    links = await load_skill_links(db, facts)
    return summarize_overview(facts, links, filters)
