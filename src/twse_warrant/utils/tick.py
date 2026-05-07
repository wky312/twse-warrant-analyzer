"""台股升降單位（tick size）.

依股價/權證價區間規則：
    < 10        → 0.01
    10  – 50    → 0.05
    50  – 100   → 0.10
    100 – 500   → 0.50
    500 – 1000  → 1.00
    >= 1000     → 5.00

權證的 tick 規則與股票相同（依權證自身價格區間）.
"""
from __future__ import annotations

from math import ceil, floor

# (上界, tick)；最後一個 None 上界代表無上限
_TICK_TABLE: list[tuple[float | None, float]] = [
    (10.0, 0.01),
    (50.0, 0.05),
    (100.0, 0.10),
    (500.0, 0.50),
    (1000.0, 1.00),
    (None, 5.00),
]


def tick_size(price: float) -> float:
    """回傳該價位的 tick 大小."""
    if price < 0:
        return 0.01
    for upper, tick in _TICK_TABLE:
        if upper is None or price < upper:
            return tick
    return 5.00


def round_to_tick(price: float, mode: str = "nearest") -> float:
    """把價格 round 到最接近 / 向下 / 向上 的 tick.

    Args:
        price: 原始價格
        mode: 'nearest' / 'down' / 'up'
    """
    if price <= 0:
        return 0.0
    t = tick_size(price)
    if mode == "down":
        return _quantize(floor(price / t) * t, t)
    if mode == "up":
        return _quantize(ceil(price / t) * t, t)
    return _quantize(round(price / t) * t, t)


def _quantize(v: float, t: float) -> float:
    """避免浮點誤差，依 tick 的精度截斷."""
    decimals = max(0, len(str(t).split(".")[-1])) if "." in str(t) else 0
    return round(v, decimals)


def adjacent_ticks(price: float) -> tuple[float, float]:
    """回傳該價位緊鄰的 (向下 tick, 向上 tick)."""
    return round_to_tick(price, "down"), round_to_tick(price, "up")
