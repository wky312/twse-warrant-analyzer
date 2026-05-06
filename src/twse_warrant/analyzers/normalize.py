"""特徵正規化：把任何指標 → 0-100."""
from __future__ import annotations

from typing import Sequence


def _safe_minmax(values: Sequence[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    return min(values), max(values)


def higher_better(values: Sequence[float]) -> list[float]:
    lo, hi = _safe_minmax(values)
    if hi == lo:
        return [50.0] * len(values)
    return [100.0 * (v - lo) / (hi - lo) for v in values]


def lower_better(values: Sequence[float]) -> list[float]:
    lo, hi = _safe_minmax(values)
    if hi == lo:
        return [50.0] * len(values)
    return [100.0 * (hi - v) / (hi - lo) for v in values]


def target(values: Sequence[float], t: float) -> list[float]:
    if not values:
        return []
    lo, hi = _safe_minmax(values)
    span = max(abs(hi - t), abs(lo - t))
    if span == 0:
        return [100.0] * len(values)
    return [100.0 * (1.0 - abs(v - t) / span) for v in values]


def target_median(values: Sequence[float]) -> list[float]:
    """target = 候選集中位數."""
    if not values:
        return []
    sorted_v = sorted(values)
    n = len(sorted_v)
    median = sorted_v[n // 2] if n % 2 == 1 else (sorted_v[n // 2 - 1] + sorted_v[n // 2]) / 2
    return target(values, median)
