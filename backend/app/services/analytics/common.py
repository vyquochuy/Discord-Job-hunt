"""Shared aggregation helpers for market analytics modules."""
from __future__ import annotations

from collections import Counter
from typing import Callable, Dict, Iterable, List, Optional, Sequence, TypeVar

from app.services.analytics.filters import JobFact
from app.services.analytics.stats import percentile_stats, salary_vnd, share

T = TypeVar("T")


def distribution_items(
    values: Iterable[str],
    labels: Dict[str, str],
    *,
    total: Optional[int] = None,
    order: Optional[Sequence[str]] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, object]]:
    counts = Counter(values)
    if order:
        ordered_keys = [key for key in order if key in counts]
        ordered_keys.extend(key for key in counts if key not in order)
    else:
        ordered_keys = [key for key, _ in counts.most_common()]
    denominator = total if total is not None else sum(counts.values())
    items = [
        {
            "value": key,
            "label": labels.get(key, key),
            "jobs": int(counts[key]),
            "share": share(counts[key], denominator),
        }
        for key in ordered_keys
    ]
    if limit is not None:
        items = items[:limit]
    return items


def group_by(
    facts: Sequence[JobFact], key: Callable[[JobFact], str]
) -> Dict[str, List[JobFact]]:
    groups: Dict[str, List[JobFact]] = {}
    for fact in facts:
        groups.setdefault(key(fact), []).append(fact)
    return groups


def salary_summary(facts: Sequence[JobFact]) -> Dict[str, object]:
    values = [
        value
        for value in (salary_vnd(f.min_salary, f.max_salary, f.salary_currency) for f in facts)
        if value is not None
    ]
    stats = percentile_stats(values)
    stats["estimated"] = any(
        (f.salary_currency or "").upper() == "USD"
        for f in facts
        if salary_vnd(f.min_salary, f.max_salary, f.salary_currency) is not None
    )
    return stats


def top_counter(counter: Counter, limit: int) -> List[str]:
    return [key for key, _ in counter.most_common(limit)]


def distinct(values: Iterable[T]) -> int:
    return len(set(values))
