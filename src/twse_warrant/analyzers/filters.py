"""硬過濾：剔除不可賣或品質太差的權證."""
from __future__ import annotations

from dataclasses import dataclass

from twse_warrant.models import Profile, Warrant


@dataclass
class FilterThresholds:
    min_days_to_expiry: int
    min_volume: int
    max_bid_ask_spread_pct: float
    max_outstanding_pct: float
    max_abs_moneyness_pct: float
    max_iv: float


PROFILE_FILTERS: dict[Profile, FilterThresholds] = {
    "stable": FilterThresholds(
        min_days_to_expiry=30,
        min_volume=50,
        max_bid_ask_spread_pct=3.0,
        max_outstanding_pct=80.0,
        max_abs_moneyness_pct=15.0,
        max_iv=80.0,
    ),
    "aggressive": FilterThresholds(
        min_days_to_expiry=14,
        min_volume=20,
        max_bid_ask_spread_pct=5.0,
        max_outstanding_pct=90.0,
        max_abs_moneyness_pct=25.0,
        max_iv=120.0,
    ),
}


def passes_filter(w: Warrant, t: FilterThresholds, *, require_greeks: bool = True) -> bool:
    """單筆 warrant 是否通過硬過濾.

    Args:
        require_greeks: True 時需有 Delta/IV 才算合格（預設）；False 時跳過 Greeks 與
            天期/價內外 條件，只看 volume/spread/流通比（用於 TWSE 等不含 Greeks 來源）.
    """
    if require_greeks:
        if w.delta is None:
            return False
        if w.iv_mid is None:
            return False
        if w.days_to_expiry is None or w.days_to_expiry < t.min_days_to_expiry:
            return False
        if w.iv_mid > t.max_iv:
            return False
        if w.moneyness_pct is not None and abs(w.moneyness_pct) > t.max_abs_moneyness_pct:
            return False
    if w.volume is None or w.volume < t.min_volume:
        return False
    if w.bid_ask_spread_pct is None or w.bid_ask_spread_pct > t.max_bid_ask_spread_pct:
        return False
    if w.outstanding_pct is not None and w.outstanding_pct > t.max_outstanding_pct:
        return False
    return True


def detect_lite_mode(warrants: list[Warrant]) -> bool:
    """若超過 80% 的 warrants 缺 Delta，視為 lite mode."""
    if not warrants:
        return False
    missing = sum(1 for w in warrants if w.delta is None)
    return missing / len(warrants) > 0.8


def apply_filters(
    warrants: list[Warrant],
    profile: Profile,
    overrides: FilterThresholds | None = None,
    *,
    lite_mode: bool | None = None,
) -> tuple[list[Warrant], int, bool]:
    """回傳 (通過清單, 因 Greeks 缺失被排除數量, 是否為 lite_mode).

    lite_mode=None 時自動偵測（>80% 缺 Greeks）.
    """
    t = overrides or PROFILE_FILTERS[profile]
    if lite_mode is None:
        lite_mode = detect_lite_mode(warrants)
    require_greeks = not lite_mode
    excluded_greeks = (
        0 if lite_mode
        else sum(1 for w in warrants if w.delta is None or w.iv_mid is None)
    )
    passed = [w for w in warrants if passes_filter(w, t, require_greeks=require_greeks)]
    return passed, excluded_greeks, lite_mode
