"""
Deterministic time bucketing for hiring-trend analytics.

Buckets are always left-closed and aligned to a natural boundary (day, ISO
week starting Monday, calendar month) so the same data produces the same chart
regardless of the request time.
"""
from __future__ import annotations

import statistics
from datetime import date, timedelta
from typing import Dict, Iterable, List, Literal, Sequence, Tuple

Granularity = Literal["day", "week", "month"]

VALID_GRANULARITIES: Tuple[str, ...] = ("auto", "day", "week", "month")


def resolve_granularity(start: date, end: date, requested: str = "auto") -> Granularity:
    if requested in ("day", "week", "month"):
        return requested  # type: ignore[return-value]
    days = max((end - start).days + 1, 1)
    if days <= 45:
        return "day"
    if days <= 180:
        return "week"
    return "month"


def bucket_start(day: date, granularity: Granularity) -> date:
    if granularity == "week":
        return day - timedelta(days=day.weekday())
    if granularity == "month":
        return day.replace(day=1)
    return day


def next_bucket(current: date, granularity: Granularity) -> date:
    if granularity == "week":
        return current + timedelta(days=7)
    if granularity == "month":
        return (current.replace(day=28) + timedelta(days=4)).replace(day=1)
    return current + timedelta(days=1)


def iter_buckets(start: date, end: date, granularity: Granularity) -> List[date]:
    if end < start:
        return []
    current = bucket_start(start, granularity)
    buckets: List[date] = []
    # Hard cap protects the endpoint from pathological ranges while still
    # covering decades at month granularity.
    limit = 1500
    while current <= end:
        if len(buckets) >= limit:
            raise ValueError("Time range exceeds 1500 buckets; use a coarser granularity.")
        buckets.append(current)
        if granularity == "month" and current.year == 9999 and current.month == 12:
            break
        if (end - current).days < (7 if granularity == "week" else 1):
            break
        current = next_bucket(current, granularity)
    return buckets


def bucket_label(day: date, granularity: Granularity) -> str:
    if granularity == "month":
        return f"Tháng {day.month:02d}/{day.year}"
    if granularity == "week":
        return f"Tuần {day.strftime('%d/%m')}"
    return day.strftime("%d/%m")


def bucket_key(day: date) -> str:
    return day.isoformat()


def count_by_bucket(
    dates: Iterable[date], buckets: Sequence[date], granularity: Granularity
) -> Dict[date, int]:
    counts: Dict[date, int] = {bucket: 0 for bucket in buckets}
    for day in dates:
        key = bucket_start(day, granularity)
        if key in counts:
            counts[key] += 1
    return counts


def daily_counts(dates: Iterable[date]) -> Dict[date, int]:
    counts: Dict[date, int] = {}
    for day in dates:
        counts[day] = counts.get(day, 0) + 1
    return counts


def detect_bulk_spikes(
    dates: Iterable[date],
    *,
    ratio_threshold: float = 3.0,
    absolute_floor: int = 25,
) -> List[Dict[str, object]]:
    """Detect days whose job count dwarfs the median posting day.

    A bulk backfill (e.g. a first full scan) creates a huge one-day spike that
    must be surfaced honestly instead of being smoothed away as "demand".
    """
    counts = daily_counts(dates)
    nonzero = [value for value in counts.values() if value > 0]
    if len(nonzero) < 3:
        return []
    median = statistics.median(nonzero)
    if median <= 0:
        return []
    threshold = max(median * ratio_threshold, absolute_floor)
    spikes: List[Dict[str, object]] = []
    for day, value in sorted(counts.items()):
        if value >= threshold:
            spikes.append(
                {
                    "date": day.isoformat(),
                    "jobs": value,
                    "median_jobs": round(median, 1),
                    "ratio": round(value / median, 1),
                }
            )
    return spikes


def spike_caveats(spikes: Sequence[Dict[str, object]]) -> List[str]:
    notes: List[str] = []
    for spike in spikes[:3]:
        notes.append(
            "Ngày {date} có {jobs} tin, gấp {ratio} lần trung vị ngày thường "
            "({median_jobs} tin). Có thể liên quan nhập dữ liệu hàng loạt/backfill; "
            "chưa xác định nguyên nhân và không thể kết luận nhu cầu tuyển dụng tăng đột biến.".format(
                date=spike["date"],
                jobs=spike["jobs"],
                ratio=spike["ratio"],
                median_jobs=spike["median_jobs"],
            )
        )
    if len(spikes) > 3:
        notes.append(f"Còn {len(spikes) - 3} ngày có spike tương tự không liệt kê hết.")
    return notes
