"""Employer Intelligence tab aggregates."""
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
from app.services.analytics.stats import (
    hhi,
    market_meta,
    share,
    status_for,
    top_share,
)
from app.services.analytics.taxonomy import CATEGORY_LABELS


def _employer_item(company: str, group: Sequence[JobFact], total: int) -> Dict[str, object]:
    salary = salary_summary(group)
    location_counter = Counter(fact.location for fact in group if fact.location)
    category_counter = Counter(fact.category for fact in group)
    dates = [fact.posted_date for fact in group if fact.posted_date]
    return {
        "company": company,
        "jobs": len(group),
        "share": share(len(group), total),
        "locations": [location for location, _ in location_counter.most_common(3)],
        "categories": [
            CATEGORY_LABELS.get(category, category)
            for category, _ in category_counter.most_common(3)
        ],
        "median_salary_vnd": salary.get("median"),
        "salary_sample": salary.get("sample_size", 0),
        "latest_post": max(dates).isoformat() if dates else None,
        "first_post": min(dates).isoformat() if dates else None,
    }


def summarize_employers(
    facts: Sequence[JobFact], filters: MarketFilters
) -> Dict[str, object]:
    total = len(facts)
    company_groups: Dict[str, List[JobFact]] = defaultdict(list)
    category_groups: Dict[str, List[JobFact]] = defaultdict(list)
    for fact in facts:
        if fact.normalized_company:
            company_groups[fact.normalized_company].append(fact)
        category_groups[fact.category].append(fact)

    ordered_companies = sorted(
        company_groups.items(), key=lambda item: len(item[1]), reverse=True
    )
    counts = [len(group) for _, group in ordered_companies]
    top_employers = [
        _employer_item(company, group, total)
        for company, group in ordered_companies[:20]
    ]

    concentration = {
        "total_companies": len(company_groups),
        "top10_share": top_share(counts, 10),
        "top20_share": top_share(counts, 20),
        "hhi": hhi(counts),
        "repeat_hirers": sum(1 for count in counts if count >= 3),
    }

    by_category: List[Dict[str, object]] = []
    for category, group in sorted(
        category_groups.items(), key=lambda item: len(item[1]), reverse=True
    )[:8]:
        employers = Counter(
            fact.normalized_company for fact in group if fact.normalized_company
        )
        by_category.append(
            {
                "category": category,
                "label": CATEGORY_LABELS.get(category, category),
                "total": len(group),
                "employers": [
                    {
                        "company": company,
                        "jobs": count,
                        "share": share(count, len(group)),
                    }
                    for company, count in employers.most_common(5)
                ],
            }
        )

    # ponytail: filtered job snapshots cannot establish first-ever company activity;
    # add entrants only when historical employer observations are available.
    new_entrants: List[Dict[str, object]] = []

    notes: List[str] = []
    if total < 30:
        notes.append(f"Mẫu nhà tuyển dụng nhỏ (N={total}); diễn giải thận trọng.")
    notes.append(
        "Tên công ty đã được chuẩn hóa bởi pipeline ingestion; các biến thể chưa gộp "
        "có thể làm phân mảnh thống kê."
    )
    notes.append(
        "Nhà tuyển dụng mới: chưa xác định; dữ liệu đã lọc không cung cấp lịch sử "
        "xuất hiện đầu tiên của công ty. Danh sách trống không có nghĩa là không có công ty mới."
    )
    notes.append(
        "Mức tập trung tính trên tin có công ty xác định; số tin không phải số vị trí tuyển thực tế."
    )

    meta = market_meta(
        filters.as_dict(),
        total_jobs=total,
        sample_size=sum(counts),
        coverage=share(sum(counts), total),
        status=status_for(sum(counts)),
        notes=notes,
    )

    return {
        "meta": meta,
        "top_employers": top_employers,
        "concentration": concentration,
        "by_category": by_category,
        "new_entrants": new_entrants,
    }


async def get_employer_intelligence(
    db: AsyncSession, filters: MarketFilters
) -> Dict[str, object]:
    facts = await load_job_facts(db, filters)
    return summarize_employers(facts, filters)
