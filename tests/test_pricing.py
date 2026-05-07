"""Black-Scholes pricing tests."""
from math import exp

import pytest

from twse_warrant.analyzers.pricing import (
    bs_price,
    fair_warrant_price,
    sensitivity_table,
)
from twse_warrant.models import Warrant


def test_bs_textbook_call():
    """經典教科書 case：S=100, K=100, T=1, r=0.05, σ=0.2 → call ≈ 10.4506."""
    p = bs_price(100, 100, 1.0, 0.05, 0.2, "call")
    assert abs(p - 10.4506) < 0.01


def test_bs_textbook_put():
    """同上 → put ≈ 5.5735."""
    p = bs_price(100, 100, 1.0, 0.05, 0.2, "put")
    assert abs(p - 5.5735) < 0.01


def test_put_call_parity():
    """C - P = S·e^(-qT) - K·e^(-rT)."""
    S, K, T, r, q, sigma = 110.0, 100.0, 0.5, 0.03, 0.01, 0.25
    c = bs_price(S, K, T, r, sigma, "call", q=q)
    p = bs_price(S, K, T, r, sigma, "put", q=q)
    expected = S * exp(-q * T) - K * exp(-r * T)
    assert abs((c - p) - expected) < 1e-6


def test_at_expiration_intrinsic_only():
    """T=0 → 純 intrinsic."""
    assert bs_price(120, 100, 0.0, 0.02, 0.3, "call") == 20.0
    assert bs_price(80, 100, 0.0, 0.02, 0.3, "call") == 0.0
    assert bs_price(80, 100, 0.0, 0.02, 0.3, "put") == 20.0


def test_zero_volatility_intrinsic_only():
    """σ=0 → 純 intrinsic."""
    assert bs_price(120, 100, 1.0, 0.02, 0.0, "call") == 20.0


def _yuanta_like(symbol="057748", strike=2218.0, ratio=0.008, last=0.71,
                 iv_buy=42.63, iv_sell=42.86, days=210, direction="call"):
    """模擬從元大 API 抓回的 Warrant."""
    return Warrant(
        symbol=symbol, name=f"權證{symbol}", underlying_symbol="2330",
        direction=direction, last_price=last, strike=strike,
        exercise_ratio=ratio, days_to_expiry=days,
        iv_buy=iv_buy, iv_sell=iv_sell,
    )


def test_fair_price_calibrates_to_market_when_using_market_iv():
    """用市場 IV + 反推現價 → BS 合理價 ≈ 市價（誤差 < 50%，因為 r/q/股息調整等差異）.

    真實案例：057748 台積電永豐5C購04
    - strike=3012.67, ratio=0.008, last=0.71, IV mid≈42.7%, days=210
    - spot 反推 ≈ 2250（深價外）
    """
    w = _yuanta_like(strike=3012.67, ratio=0.008, last=0.71,
                     iv_buy=42.63, iv_sell=42.86, days=210)
    res = fair_warrant_price(w, spot=2250.0, r=0.02)
    assert res is not None
    assert res.market_price == 0.71
    # 容忍 50% 偏差：BS 與券商 IV calibration 之間的常見差異
    assert abs(res.deviation_pct) < 50.0


def test_fair_price_exercise_ratio_applied():
    """per-share BS × ratio = per-warrant 合理價."""
    w = _yuanta_like(strike=100, ratio=0.5, last=5.0,
                     iv_buy=20, iv_sell=20, days=365)
    res = fair_warrant_price(w, spot=100, r=0.05)
    bs_per_share = bs_price(100, 100, 365/365.25, 0.05, 0.2, "call")
    assert res is not None
    assert abs(res.fair_price - bs_per_share * 0.5) < 1e-6


def test_fair_price_returns_none_when_missing_data():
    w = _yuanta_like()
    w.strike = None
    assert fair_warrant_price(w, spot=2250) is None
    w2 = _yuanta_like()
    w2.exercise_ratio = 0
    assert fair_warrant_price(w2, spot=2250) is None
    w3 = _yuanta_like(iv_buy=None, iv_sell=None)
    assert fair_warrant_price(w3, spot=2250) is None


def test_call_fair_price_monotone_in_spot():
    """Call 合理價對 spot 應單調遞增."""
    w = _yuanta_like(strike=2300, ratio=0.005, days=120,
                     iv_buy=40, iv_sell=40)
    prices = [
        fair_warrant_price(w, spot=s).fair_price
        for s in (2200, 2250, 2300, 2350, 2400)
    ]
    for a, b in zip(prices, prices[1:]):
        assert a <= b


def test_put_fair_price_monotone_in_spot():
    """Put 合理價對 spot 應單調遞減."""
    w = _yuanta_like(strike=2300, ratio=0.005, days=120,
                     iv_buy=40, iv_sell=40, direction="put")
    prices = [
        fair_warrant_price(w, spot=s).fair_price
        for s in (2200, 2250, 2300, 2350, 2400)
    ]
    for a, b in zip(prices, prices[1:]):
        assert a >= b


def test_sensitivity_table_basic():
    w = _yuanta_like(strike=2300, ratio=0.005, days=120,
                     iv_buy=40, iv_sell=40, last=2.0)
    steps = [-10, -5, 0, 5, 10]
    out = sensitivity_table(w, spot_center=2250, spot_steps=steps)
    assert len(out) == 5
    # 第一欄 spot
    assert [s for s, _ in out] == [2240, 2245, 2250, 2255, 2260]
    # call 單調遞增
    prices = [p for _, p in out if p is not None]
    for a, b in zip(prices, prices[1:]):
        assert a <= b


def test_iv_higher_means_higher_price():
    """Vega > 0：IV 上升 → 合理價上升（at-the-money 最明顯）."""
    w = _yuanta_like(strike=2250, ratio=0.005, last=2.0, days=90)
    p_low = fair_warrant_price(w, spot=2250, iv_pct=30.0).fair_price
    p_high = fair_warrant_price(w, spot=2250, iv_pct=60.0).fair_price
    assert p_high > p_low
