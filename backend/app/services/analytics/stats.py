"""
Small deterministic statistics helpers shared by every market analytics module.

No external statistics dependency: the dataset sizes are small and the exact
percentile definition must stay stable across environments/tests.
"""
from __future__ import annotations

import math
from typing import Dict, Iterable, Optional, Sequence

from app.core.config import settings


def safe_div(numerator: float, denominator: float) -> float:
    if not denominator:
        return 0.0
    return numerator / denominator


def share(part: float, whole: float) -> float:
    return round(safe_div(float(part), float(whole)), 4)


def percentile(values: Sequence[float], p: float) -> Optional[float]:
    """Linear-interpolation percentile (same definition as numpy's default)."""
    if not values:
        return None
    if p <= 0:
        return float(min(values))
    if p >= 1:
        return float(max(values))
    ordered = sorted(float(v) for v in values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * p
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[int(position)]
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def percentile_stats(values: Sequence[float]) -> Dict[str, Optional[float]]:
    clean = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    if not clean:
        return {
            "sample_size": 0,
            "min": None,
            "p25": None,
            "median": None,
            "p75": None,
            "max": None,
            "mean": None,
        }
    return {
        "sample_size": len(clean),
        "min": round(min(clean), 2),
        "p25": round(percentile(clean, 0.25) or 0.0, 2),
        "median": round(percentile(clean, 0.50) or 0.0, 2),
        "p75": round(percentile(clean, 0.75) or 0.0, 2),
        "max": round(max(clean), 2),
        "mean": round(sum(clean) / len(clean), 2),
    }


def status_for(
    sample_size: int,
    coverage: float = 1.0,
    *,
    min_sample: Optional[int] = None,
    min_coverage: float = 0.0,
) -> str:
    """Return one of ok / insufficient / empty.

    `unavailable` is reserved for a dimension that does not exist in the source
    data at all; modules use it explicitly when they cannot compute a metric.
    """
    if sample_size <= 0:
        return "empty"
    threshold = settings.MARKET_MIN_SAMPLE if min_sample is None else min_sample
    if sample_size < threshold or coverage < min_coverage:
        return "insufficient"
    return "ok"


def market_meta(
    filters: Dict[str, object],
    *,
    total_jobs: int,
    sample_size: int,
    coverage: float,
    status: str,
    notes: Optional[Iterable[str]] = None,
) -> Dict[str, object]:
    from datetime import datetime, timezone

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filters": filters,
        "total_jobs": int(total_jobs),
        "sample_size": int(sample_size),
        "coverage": round(float(coverage), 4),
        "status": status,
        "notes": list(notes or []),
    }


# ---------------------------------------------------------------------------
# Salary helpers
# ---------------------------------------------------------------------------
SUPPORTED_CURRENCIES = {"VND", "USD"}


def native_midpoint(min_salary: Optional[float], max_salary: Optional[float]) -> Optional[float]:
    """Midpoint of a salary range in its native currency.

    Using the midpoint avoids biasing the median toward either bound when only
    one side of a range is present. Single-sided ranges use the available bound.
    """
    bounds = [float(v) for v in (min_salary, max_salary) if v is not None]
    if any(not math.isfinite(v) or v <= 0 for v in bounds):
        return None
    if min_salary is not None and max_salary is not None:
        if min_salary > max_salary:
            return None
        return (float(min_salary) + float(max_salary)) / 2.0
    if max_salary is not None:
        return float(max_salary)
    if min_salary is not None:
        return float(min_salary)
    return None


def normalize_to_vnd(amount: Optional[float], currency: Optional[str]) -> Optional[float]:
    if amount is None:
        return None
    code = (currency or "").strip().upper()
    if code == "VND":
        return float(amount)
    if code == "USD":
        return float(amount) * float(settings.MARKET_USD_TO_VND)
    return None


def salary_vnd(
    min_salary: Optional[float],
    max_salary: Optional[float],
    currency: Optional[str],
) -> Optional[float]:
    return normalize_to_vnd(native_midpoint(min_salary, max_salary), currency)


def hhi(counts: Iterable[int]) -> float:
    """Herfindahl-Hirschman Index on a 0-10000 scale."""
    values = [int(c) for c in counts if c > 0]
    total = sum(values)
    if not total:
        return 0.0
    return round(sum((value / total) ** 2 for value in values) * 10000, 1)


def top_share(counts: Sequence[int], top_n: int) -> float:
    values = sorted((int(c) for c in counts if c > 0), reverse=True)
    total = sum(values)
    if not total:
        return 0.0
    return round(sum(values[:top_n]) / total, 4)


def histogram_bucket(value: float, buckets: Sequence[tuple]) -> str:
    """Return the label of the first bucket whose upper bound covers value."""
    for label, lower, upper in buckets:
        if lower is not None and value < lower:
            continue
        if upper is not None and value >= upper:
            continue
        return label
    return buckets[-1][0]


def coerce_float(value: object) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def counter_dict(counter) -> Dict[str, int]:
    return {str(key): int(value) for key, value in counter.items()}
