"""Hiring Trends tab aggregates."""
from __future__ import annotations

from collections import Counter
from typing import Dict, List, Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.analytics.buckets import (
    bucket_label,
    bucket_start,
    count_by_bucket,
    detect_bulk_spikes,
    iter_buckets,
    resolve_granularity,
    spike_caveats,
)
from app.services.analytics.common import distribution_items
from app.services.analytics.filters import (
    JobFact,
    MarketFilters,
    load_job_facts,
    previous_period,
    resolve_range,
    with_previous_period,
)
from app.services.analytics.stats import market_meta, share, status_for
from app.services.analytics.taxonomy import (
    CATEGORY_LABELS,
    LEVEL_LABELS,
    LEVEL_ORDER,
    WORK_MODE_LABELS,
)


def summarize_hiring_trends(
    facts: Sequence[JobFact],
    previous_facts: Optional[Sequence[JobFact]],
    filters: MarketFilters,
    granularity: str = "auto",
) -> Dict[str, object]:
    total = len(facts)
    dates = [fact.posted_date for fact in facts if fact.posted_date is not None]
    start, end = resolve_range(facts, filters)
    notes: List[str] = [
        "Số 0 là không có tin quan sát được, không có nghĩa là không có nhu cầu tuyển dụng."
    ]
    if not filters.include_expired:
        notes.append(
            "Chỉ xét tin hiện ACTIVE: xu hướng có thiên lệch sống sót, không phải lịch sử "
            "toàn bộ tin từng được đăng."
        )

    if start is None or end is None or start > end:
        meta = market_meta(
            filters.as_dict(),
            total_jobs=total,
            sample_size=len(dates),
            coverage=share(len(dates), total),
            status=status_for(len(dates), share(len(dates), total), min_coverage=0.5),
            notes=notes + ["Không có dữ liệu posted_at trong phạm vi bộ lọc."],
        )
        return {
            "meta": meta,
            "series": [],
            "stacked": [],
            "sources": [],
            "categories": [],
            "levels": [],
            "work_modes": [],
            "summary": {
                "total_jobs": total,
                "bucket_count": 0,
                "avg_per_bucket": 0,
                "peak": None,
                "latest": None,
                "previous_period": None,
                "granularity": granularity,
            },
            "caveats": meta["notes"],
        }

    resolved = resolve_granularity(start, end, granularity)
    try:
        buckets = iter_buckets(start, end, resolved)
    except ValueError:
        resolved = "month"
        buckets = iter_buckets(start, end, resolved)
        notes.append("Khoảng thời gian quá dài; biểu đồ được gộp theo tháng thay vì cắt bớt dữ liệu.")
    counts = count_by_bucket(dates, buckets, resolved)

    series = [
        {
            "bucket": bucket.isoformat(),
            "label": bucket_label(bucket, resolved),
            "jobs": int(counts[bucket]),
        }
        for bucket in buckets
    ]

    # Stacked series by source (top 5 + other) so the frontend can render a
    # composition chart without shipping a full source x bucket matrix.
    source_totals = Counter(fact.source for fact in facts)
    top_sources = [source for source, _ in source_totals.most_common(5)]
    source_bucket_counts: Counter = Counter()
    for fact in facts:
        if fact.posted_date is None:
            continue
        source_bucket_counts[(fact.source, bucket_start(fact.posted_date, resolved))] += 1
    stacked: List[Dict[str, object]] = []
    for bucket in buckets:
        values = {
            source: int(source_bucket_counts.get((source, bucket), 0))
            for source in top_sources
        }
        other = int(counts[bucket]) - sum(values.values())
        values["other"] = max(other, 0)
        stacked.append(
            {
                "bucket": bucket.isoformat(),
                "label": bucket_label(bucket, resolved),
                "values": values,
            }
        )

    peak_bucket = max(buckets, key=lambda bucket: counts[bucket]) if buckets else None
    peak = (
        {
            "bucket": peak_bucket.isoformat(),
            "label": bucket_label(peak_bucket, resolved),
            "jobs": int(counts[peak_bucket]),
        }
        if peak_bucket is not None
        else None
    )
    latest_bucket = buckets[-1] if buckets else None
    latest = (
        {
            "bucket": latest_bucket.isoformat(),
            "label": bucket_label(latest_bucket, resolved),
            "jobs": int(counts[latest_bucket]),
        }
        if latest_bucket is not None
        else None
    )

    previous_period_payload = None
    if previous_facts is not None:
        previous_start, previous_end = previous_period(start, end)
        previous_total = len(previous_facts)
        change_pct = (
            round((total - previous_total) / previous_total * 100, 1)
            if previous_total
            else None
        )
        previous_period_payload = {
            "start": previous_start.isoformat(),
            "end": previous_end.isoformat(),
            "jobs": previous_total,
            "change_pct": change_pct,
        }

    spikes = detect_bulk_spikes(dates)
    notes.extend(spike_caveats(spikes))
    missing_posted = total - len(dates)
    if missing_posted:
        notes.append(
            f"{missing_posted}/{total} tin không có posted_at nên không xuất hiện trên biểu đồ."
        )
    if not filters.has_date_filter:
        notes.append(
            "Khoảng thời gian được suy ra từ posted_at nhỏ nhất/lớn nhất trong dữ liệu."
        )
    if total < 30:
        notes.append(
            f"Mẫu xu hướng nhỏ (N={total}); diễn giải thận trọng."
        )

    coverage = share(len(dates), total)
    meta = market_meta(
        filters.as_dict(),
        total_jobs=total,
        sample_size=len(dates),
        coverage=coverage,
        status=status_for(len(dates), coverage, min_coverage=0.5),
        notes=notes,
    )

    return {
        "meta": meta,
        "series": series,
        "stacked": stacked,
        "sources": distribution_items(
            (fact.source for fact in facts),
            {fact.source: fact.source for fact in facts},
            total=total,
        ),
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
        "work_modes": distribution_items(
            (fact.work_mode for fact in facts),
            WORK_MODE_LABELS,
            total=total,
            order=["ONSITE", "HYBRID", "REMOTE"],
        ),
        "summary": {
            "total_jobs": total,
            "bucket_count": len(buckets),
            "avg_per_bucket": round(len(dates) / len(buckets), 1) if buckets else 0,
            "peak": peak,
            "latest": latest,
            "previous_period": previous_period_payload,
            "granularity": resolved,
        },
        "caveats": notes,
    }


async def get_hiring_trends(
    db: AsyncSession, filters: MarketFilters, granularity: str = "auto"
) -> Dict[str, object]:
    facts = await load_job_facts(db, filters)
    start, end = resolve_range(facts, filters)
    previous_facts: Optional[List[JobFact]] = None
    if start is not None and end is not None and start <= end:
        previous_filters = with_previous_period(filters, start, end)
        previous_facts = await load_job_facts(db, previous_filters)
    return summarize_hiring_trends(facts, previous_facts, filters, granularity)
