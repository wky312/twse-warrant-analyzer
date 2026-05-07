"""Black-Scholes 權證合理價計算.

主要使用情境：盤中標的價跳動時，估算權證的「合理掛單價」。

公式：歐式選擇權 BS（含股息率）。台灣權證多為美式但無股息 call 等同歐式；
有股息或深價內 put 略有差異，對限價單的精度足夠。
"""
from __future__ import annotations

from dataclasses import dataclass
from math import exp, log, sqrt
from statistics import NormalDist
from typing import Optional, Sequence

from twse_warrant.models import Direction, Warrant

_NORM = NormalDist()


def bs_price(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    direction: Direction,
    q: float = 0.0,
) -> float:
    """歐式選擇權 BS 公式（per-share，未乘行使比例）.

    Args:
        S: 標的價
        K: 履約價
        T: 到期年化（days/365.25）
        r: 無風險利率（小數，例 0.02）
        sigma: 隱含波動度（小數，例 0.45）
        direction: 'call' / 'put'
        q: 股息率（小數），預設 0
    """
    if T <= 0 or sigma <= 0:
        if direction == "call":
            return max(S - K, 0.0)
        return max(K - S, 0.0)
    sqrt_t = sqrt(T)
    d1 = (log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * sqrt_t)
    d2 = d1 - sigma * sqrt_t
    if direction == "call":
        return S * exp(-q * T) * _NORM.cdf(d1) - K * exp(-r * T) * _NORM.cdf(d2)
    return K * exp(-r * T) * _NORM.cdf(-d2) - S * exp(-q * T) * _NORM.cdf(-d1)


@dataclass
class FairPriceResult:
    fair_price: float                         # BS 合理價（per warrant）
    intrinsic: float                          # 內含值
    time_value: float                         # 時間價值
    days_to_expiry: int
    iv_used_pct: float
    spot_used: float
    market_price: Optional[float] = None
    deviation_pct: Optional[float] = None     # (fair - market) / market * 100


def fair_warrant_price(
    w: Warrant,
    spot: float,
    iv_pct: Optional[float] = None,
    days: Optional[int] = None,
    r: float = 0.02,
    q: float = 0.0,
) -> Optional[FairPriceResult]:
    """高階介面：吃 Warrant 物件 + 標的價，回傳合理 per-warrant 價.

    Args:
        w: Warrant
        spot: 標的價（盤中即時或假設值）
        iv_pct: 用百分比表示的 IV（例 45 = 45%）；None 時用 w.iv_mid
        days: 剩餘天數；None 時用 w.days_to_expiry
        r: 無風險利率（小數）
        q: 股息率（小數）

    Returns:
        FairPriceResult 或 None（資料缺失時）
    """
    if w.strike is None or w.exercise_ratio is None or w.exercise_ratio <= 0:
        return None
    if spot <= 0:
        return None
    iv = iv_pct if iv_pct is not None else w.iv_mid
    if iv is None or iv <= 0:
        return None
    d = days if days is not None else w.days_to_expiry
    if d is None or d < 0:
        return None
    T = max(d, 0) / 365.25
    sigma = iv / 100.0
    per_share = bs_price(spot, w.strike, T, r, sigma, w.direction, q=q)
    fair = per_share * w.exercise_ratio
    intrinsic = (
        max(spot - w.strike, 0.0) if w.direction == "call"
        else max(w.strike - spot, 0.0)
    ) * w.exercise_ratio
    time_value = max(fair - intrinsic, 0.0)
    deviation = None
    if w.last_price and w.last_price > 0:
        deviation = (fair - w.last_price) / w.last_price * 100.0
    return FairPriceResult(
        fair_price=fair,
        intrinsic=intrinsic,
        time_value=time_value,
        days_to_expiry=int(d),
        iv_used_pct=iv,
        spot_used=spot,
        market_price=w.last_price,
        deviation_pct=deviation,
    )


def sensitivity_table(
    w: Warrant,
    spot_center: float,
    spot_steps: Sequence[float],
    iv_pct: Optional[float] = None,
    days: Optional[int] = None,
    r: float = 0.02,
    q: float = 0.0,
) -> list[tuple[float, Optional[float]]]:
    """股價 ± Δ 元，回傳對應合理價清單.

    Returns:
        list of (新標的價, 合理權證價 or None)
    """
    out: list[tuple[float, Optional[float]]] = []
    for ds in spot_steps:
        s = spot_center + ds
        if s <= 0:
            out.append((s, None))
            continue
        result = fair_warrant_price(w, s, iv_pct=iv_pct, days=days, r=r, q=q)
        out.append((s, result.fair_price if result else None))
    return out
