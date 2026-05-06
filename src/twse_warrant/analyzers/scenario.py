"""情境模擬：給定目標標的價 + 目標天期，計算每檔權證的預期報酬與風險.

模型（簡化但合理）：
    intrinsic(S) = max(S - K, 0) × ratio        (call)
    intrinsic(S) = max(K - S, 0) × ratio        (put)
    time_value_now = W_now - intrinsic(S_now)
    在達到 S_target 的目標日，剩餘到期天數 T_remain = days_to_expiry - days_to_target
    若 T_remain <= 0：W_at_target = intrinsic(S_target)         （已到期）
    否則：W_at_target = intrinsic(S_target) + time_value_now × sqrt(T_remain / days_to_expiry)
        （時間價值以 sqrt(t) 衰減，合理近似 Black-Scholes 行為）

也輸出風險情境：標的不動 / 下跌 5% / 下跌 10% 各對應的權證價與報酬率.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt
from typing import Optional

from twse_warrant.models import Direction, Warrant


@dataclass
class ScenarioInputs:
    target_price: float           # 目標標的價
    days_to_target: int           # 預期幾天到達
    spot_now: Optional[float] = None  # 標的現價（None 時用 warrant.last_price 反推不到，需另傳）
    risk_drops_pct: tuple[float, ...] = (0.0, -5.0, -10.0)


@dataclass
class ScenarioResult:
    warrant: Warrant
    breakeven: Optional[float]              # 損益兩平標的價
    intrinsic_at_target: Optional[float]    # 達標時內含值（每張權證）
    expected_warrant_price: Optional[float] # 達標時預期權證價
    expected_return_pct: Optional[float]    # 達標時報酬率 (%)
    risk_returns: dict[float, Optional[float]] = field(default_factory=dict)  # %drop → return%
    notes: list[str] = field(default_factory=list)


def _intrinsic(direction: Direction, S: float, K: float, ratio: float) -> float:
    if direction == "call":
        return max(S - K, 0.0) * ratio
    if direction == "put":
        return max(K - S, 0.0) * ratio
    return 0.0


def _project_warrant_price(
    w: Warrant,
    spot_target: float,
    days_to_target: int,
    spot_now: float,
) -> Optional[float]:
    """估算在達到 spot_target 的目標日時，權證價會是多少."""
    if (
        w.strike is None
        or w.exercise_ratio is None
        or w.exercise_ratio <= 0
        or w.last_price is None
        or w.days_to_expiry is None
    ):
        return None
    K = w.strike
    ratio = w.exercise_ratio
    intrinsic_now = _intrinsic(w.direction, spot_now, K, ratio)
    time_value_now = max(w.last_price - intrinsic_now, 0.0)

    intrinsic_target = _intrinsic(w.direction, spot_target, K, ratio)
    t_remain = w.days_to_expiry - days_to_target
    if t_remain <= 0:
        return intrinsic_target
    if w.days_to_expiry <= 0:
        return intrinsic_target
    decay_factor = sqrt(max(t_remain, 0) / w.days_to_expiry)
    return intrinsic_target + time_value_now * decay_factor


def compute_breakeven(w: Warrant) -> Optional[float]:
    if w.strike is None or w.exercise_ratio is None or w.exercise_ratio <= 0 or w.last_price is None:
        return None
    if w.direction == "call":
        return w.strike + w.last_price / w.exercise_ratio
    if w.direction == "put":
        return w.strike - w.last_price / w.exercise_ratio
    return None


def evaluate_scenario(
    w: Warrant,
    inputs: ScenarioInputs,
) -> ScenarioResult:
    """單一權證的情境評估."""
    spot_now = inputs.spot_now
    if spot_now is None:
        # 嘗試從 moneyness_pct + strike 反推
        if w.strike is not None and w.moneyness_pct is not None:
            if w.direction == "call":
                # moneyness_pct = (S - K) / K * 100
                spot_now = w.strike * (1 + w.moneyness_pct / 100.0)
            elif w.direction == "put":
                # moneyness_pct (put) = (K - S) / K * 100 (per our convention from Yuanta)
                spot_now = w.strike * (1 - w.moneyness_pct / 100.0)
    notes: list[str] = []
    if spot_now is None:
        return ScenarioResult(
            warrant=w,
            breakeven=compute_breakeven(w),
            intrinsic_at_target=None,
            expected_warrant_price=None,
            expected_return_pct=None,
            notes=["缺現價，無法估算"],
        )

    be = compute_breakeven(w)
    intrinsic_target = (
        _intrinsic(w.direction, inputs.target_price, w.strike, w.exercise_ratio)
        if w.strike is not None and w.exercise_ratio
        else None
    )
    expected_W = _project_warrant_price(w, inputs.target_price, inputs.days_to_target, spot_now)
    expected_return = None
    if expected_W is not None and w.last_price and w.last_price > 0:
        expected_return = (expected_W - w.last_price) / w.last_price * 100.0

    risk_returns: dict[float, Optional[float]] = {}
    for drop_pct in inputs.risk_drops_pct:
        risk_spot = spot_now * (1 + drop_pct / 100.0)
        risk_W = _project_warrant_price(w, risk_spot, inputs.days_to_target, spot_now)
        if risk_W is None or w.last_price is None or w.last_price <= 0:
            risk_returns[drop_pct] = None
        else:
            risk_returns[drop_pct] = (risk_W - w.last_price) / w.last_price * 100.0

    if be is not None:
        if w.direction == "call" and inputs.target_price < be:
            notes.append(f"目標 {inputs.target_price:.0f} < 損益兩平 {be:.0f}：對也賠")
        if w.direction == "put" and inputs.target_price > be:
            notes.append(f"目標 {inputs.target_price:.0f} > 損益兩平 {be:.0f}：對也賠")

    if w.days_to_expiry is not None and w.days_to_expiry < inputs.days_to_target:
        notes.append(f"剩餘天數 {w.days_to_expiry} 天 < 目標天期 {inputs.days_to_target}：將以到期內含值估算")

    return ScenarioResult(
        warrant=w,
        breakeven=be,
        intrinsic_at_target=intrinsic_target,
        expected_warrant_price=expected_W,
        expected_return_pct=expected_return,
        risk_returns=risk_returns,
        notes=notes,
    )


@dataclass
class ScenarioBatchResult:
    """情境批次結果，含過濾統計."""
    results: list["ScenarioResult"]
    excluded_too_short: int = 0           # 因到期早於目標日被剃除
    excluded_low_volume: int = 0
    excluded_wide_spread: int = 0
    excluded_no_profit: int = 0


def evaluate_scenarios(
    warrants: list[Warrant],
    inputs: ScenarioInputs,
    *,
    require_alive_at_target: bool = True,
    require_profit_at_target: bool = True,
    min_volume: int = 50,
    max_spread_pct: float = 5.0,
    sort_by: str = "expected_return",  # "expected_return" / "breakeven_distance"
) -> ScenarioBatchResult:
    """批次跑情境，過濾並排序.

    require_alive_at_target=True 時，到期日早於目標天期的權證會被直接剃除
    （無法持有到目標日 → 對該情境無意義）.
    """
    out: list[ScenarioResult] = []
    excluded_too_short = 0
    excluded_low_volume = 0
    excluded_wide_spread = 0
    excluded_no_profit = 0

    for w in warrants:
        # 1. 天期：到期日必須晚於目標日
        if require_alive_at_target:
            if w.days_to_expiry is None or w.days_to_expiry < inputs.days_to_target:
                excluded_too_short += 1
                continue
        # 2. 流動性
        if w.volume is None or w.volume < min_volume:
            excluded_low_volume += 1
            continue
        if w.bid_ask_spread_pct is None or w.bid_ask_spread_pct > max_spread_pct:
            excluded_wide_spread += 1
            continue

        r = evaluate_scenario(w, inputs)

        # 3. 達標時要有正報酬
        if require_profit_at_target:
            if r.expected_return_pct is None or r.expected_return_pct <= 0:
                excluded_no_profit += 1
                continue
        out.append(r)

    if sort_by == "expected_return":
        out.sort(key=lambda r: r.expected_return_pct or -1e9, reverse=True)
    elif sort_by == "breakeven_distance":
        # 損益兩平離目標越遠（call 是 BE 越低、put 是 BE 越高）越好
        def be_score(r: ScenarioResult) -> float:
            if r.breakeven is None:
                return -1e9
            if r.warrant.direction == "call":
                return inputs.target_price - r.breakeven
            return r.breakeven - inputs.target_price
        out.sort(key=be_score, reverse=True)
    return ScenarioBatchResult(
        results=out,
        excluded_too_short=excluded_too_short,
        excluded_low_volume=excluded_low_volume,
        excluded_wide_spread=excluded_wide_spread,
        excluded_no_profit=excluded_no_profit,
    )
