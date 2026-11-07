"""Salary Intelligence tab aggregates."""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.analytics.filters import JobFact, MarketFilters, load_job_facts
from app.services.analytics.stats import (
    SUPPORTED_CURRENCIES,
    market_meta,
    native_midpoint,
    percentile_stats,
    salary_vnd,
    share,
    status_for,
)
from app.services.analytics.taxonomy import (
    CATEGORY_LABELS,
    LEVEL_LABELS,
    LEVEL_ORDER,
    REGION_LABELS,
)

SALARY_HISTOGRAM_BUCKETS = [
    ("< 10 triệu", None, 10_000_000),
    ("10–15 triệu", 10_000_000, 15_000_000),
    ("15–20 triệu", 15_000_000, 20_000_000),
    ("20–30 triệu", 20_000_000, 30_000_000),
    ("30–40 triệu", 30_000_000, 40_000_000),
    ("40–60 triệu", 40_000_000, 60_000_000),
    ("60–100 triệu", 60_000_000, 100_000_000),
    (">= 100 triệu", 100_000_000, None),
]


def _fact_currency(fact: JobFact) -> str:
    return (fact.salary_currency or "").strip().upper()


def _fact_has_valid_salary(fact: JobFact) -> bool:
    return (
        _fact_currency(fact) in SUPPORTED_CURRENCIES
        and salary_vnd(fact.min_salary, fact.max_salary, fact.salary_currency) is not None
    )


def _vnd_values(facts: Sequence[JobFact]) -> List[float]:
    values: List[float] = []
    for fact in facts:
        value = salary_vnd(fact.min_salary, fact.max_salary, fact.salary_currency)
        if value is not None:
            values.append(value)
    return values


def _salary_group(
    key: str,
    label: str,
    facts: Sequence[JobFact],
    *,
    min_sample: int = 3,
) -> Optional[Dict[str, object]]:
    values = _vnd_values(facts)
    if not values:
        return None
    stats = percentile_stats(values)
    stats.update(
        {
            "key": key,
            "label": label,
            "jobs": len(facts),
            "salary_sample": len(values),
            "estimated": any(_fact_currency(fact) == "USD" for fact in facts),
            "status": status_for(len(values), min_sample=min_sample),
        }
    )
    return stats


def _group_salary(
    facts: Sequence[JobFact],
    key_fn,
    label_fn,
    *,
    limit: Optional[int] = None,
    min_sample: int = 3,
) -> List[Dict[str, object]]:
    groups: Dict[str, List[JobFact]] = defaultdict(list)
    for fact in facts:
        groups[key_fn(fact)].append(fact)
    items: List[Dict[str, object]] = []
    for key, group in groups.items():
        item = _salary_group(key, label_fn(key), group, min_sample=min_sample)
        if item is not None:
            items.append(item)
    items.sort(key=lambda item: item.get("median") or 0, reverse=True)
    return items[:limit] if limit is not None else items


def summarize_salary(
    facts: Sequence[JobFact], filters: MarketFilters
) -> Dict[str, object]:
    total = len(facts)
    valid = [fact for fact in facts if _fact_has_valid_salary(fact)]
    unknown_currency = [
        fact
        for fact in facts
        if fact.has_salary_amount and _fact_currency(fact) not in SUPPORTED_CURRENCIES
    ]
    negotiable = [
        fact
        for fact in facts
        if not fact.has_salary_amount and fact.is_salary_negotiable
    ]
    missing = [
        fact
        for fact in facts
        if not fact.has_salary_amount and not fact.is_salary_negotiable
    ]

    native: List[Dict[str, object]] = []
    for currency in ("VND", "USD"):
        currency_facts = [fact for fact in valid if _fact_currency(fact) == currency]
        values = [
            value
            for value in (
                native_midpoint(fact.min_salary, fact.max_salary)
                for fact in currency_facts
            )
            if value is not None
        ]
        if not values:
            continue
        stats = percentile_stats(values)
        stats.update(
            {
                "currency": currency,
                "jobs": len(currency_facts),
                "estimated": False,
                "status": status_for(len(values), min_sample=3),
            }
        )
        native.append(stats)

    vnd_values = _vnd_values(valid)
    normalized_vnd = percentile_stats(vnd_values)
    normalized_vnd.update(
        {
            "currency": "VND",
            "fx_rate": float(settings.MARKET_USD_TO_VND),
            "fx_source": "MARKET_USD_TO_VND (cấu hình hệ thống)",
            "usd_jobs": sum(1 for fact in valid if _fact_currency(fact) == "USD"),
            "estimated": any(_fact_currency(fact) == "USD" for fact in valid),
            "status": status_for(len(vnd_values), min_sample=3),
        }
    )

    histogram = []
    for label, lower, upper in SALARY_HISTOGRAM_BUCKETS:
        count = sum(
            1
            for value in vnd_values
            if (lower is None or value >= lower) and (upper is None or value < upper)
        )
        histogram.append(
            {"label": label, "min": lower, "max": upper, "count": count}
        )

    by_level = _group_salary(
        valid,
        lambda fact: fact.level,
        lambda key: LEVEL_LABELS.get(key, key),
        min_sample=3,
    )
    # Keep a stable seniority order for the UI where possible.
    by_level.sort(
        key=lambda item: (
            LEVEL_ORDER.index(str(item["key"]))
            if str(item["key"]) in LEVEL_ORDER
            else len(LEVEL_ORDER)
        )
    )

    by_category = _group_salary(
        valid,
        lambda fact: fact.category,
        lambda key: CATEGORY_LABELS.get(key, key),
        limit=10,
        min_sample=3,
    )
    by_region = _group_salary(
        valid,
        lambda fact: fact.region,
        lambda key: REGION_LABELS.get(key, key),
        limit=8,
        min_sample=3,
    )
    by_source = _group_salary(
        valid,
        lambda fact: fact.source,
        lambda key: key,
        min_sample=3,
    )
    top_companies = _group_salary(
        valid,
        lambda fact: fact.normalized_company,
        lambda key: key,
        limit=10,
        min_sample=2,
    )

    coverage = share(len(valid), total)
    notes: List[str] = []
    if total and coverage < 0.25:
        notes.append(
            f"Chỉ {len(valid)}/{total} tin ({coverage * 100:.1f}%) có dữ liệu lương hợp lệ. "
            "Các chỉ số lương chỉ phản ánh nhóm tin có công bố lương, không đại diện toàn thị trường."
        )
    if normalized_vnd["usd_jobs"]:
        notes.append(
            f"{normalized_vnd['usd_jobs']} tin trả bằng USD được quy đổi sang VND theo tỷ giá "
            f"1 USD = {settings.MARKET_USD_TO_VND:,.0f} VND; đây là giá trị ước tính (estimated)."
        )
    if len(vnd_values) < settings.MARKET_SALARY_MIN_SAMPLE:
        notes.append(
            f"Mẫu lương nhỏ (N={len(vnd_values)}); không nên suy rộng ra toàn thị trường."
        )
    if negotiable:
        notes.append(
            f"{len(negotiable)} tin ghi 'thỏa thuận' không được đưa vào thống kê lương."
        )
    invalid_salary = total - len(valid) - len(unknown_currency) - len(negotiable) - len(missing)
    if invalid_salary:
        notes.append(
            f"{invalid_salary} tin có khoảng lương không hợp lệ (không hữu hạn, không dương "
            "hoặc min lớn hơn max); bị loại khỏi thống kê lương."
        )
    if unknown_currency:
        notes.append(
            f"{len(unknown_currency)} tin có số tiền nhưng đơn vị tiền tệ không xác định; "
            "không được quy đổi để tránh sai lệch."
        )
    notes.append(
        "Giá trị lương dùng midpoint của khoảng min–max; tin chỉ có một đầu mút dùng "
        "đầu mút làm proxy giới hạn, không phải midpoint hay mức lương thực trả."
    )
    notes.append(
        "Schema chưa có chu kỳ trả lương (tháng/năm/giờ) hoặc gross/net; không thể "
        "quy đổi, phân biệt hay bảo đảm khả năng so sánh các mức lương này."
    )

    meta = market_meta(
        filters.as_dict(),
        total_jobs=total,
        sample_size=len(valid),
        coverage=coverage,
        status=status_for(
            len(valid),
            coverage,
            min_sample=settings.MARKET_SALARY_MIN_SAMPLE,
            min_coverage=0.1,
        ),
        notes=notes,
    )

    return {
        "meta": meta,
        "coverage": {
            "with_salary": len(valid),
            "total": total,
            "ratio": coverage,
            "negotiable": len(negotiable),
            "unknown_currency": len(unknown_currency),
            "missing": len(missing),
        },
        "native": native,
        "normalized_vnd": normalized_vnd,
        "by_level": by_level,
        "by_category": by_category,
        "by_region": by_region,
        "by_source": by_source,
        "histogram": histogram,
        "top_companies": top_companies,
        "notes": notes,
    }


async def get_salary_intelligence(
    db: AsyncSession, filters: MarketFilters
) -> Dict[str, object]:
    facts = await load_job_facts(db, filters)
    return summarize_salary(facts, filters)
