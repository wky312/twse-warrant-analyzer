"""情境模擬測試."""
from datetime import date

import pytest

from twse_warrant.analyzers.scenario import (
    ScenarioInputs,
    compute_breakeven,
    evaluate_scenario,
    evaluate_scenarios,
)
from twse_warrant.models import Warrant


def _call(symbol: str, strike: float, ratio: float, last: float, days: int = 60,
          spot_implied_via_moneyness: float = 0.0, volume: int = 200,
          spread: float = 1.0) -> Warrant:
    """建一檔合成認購權證。spot_implied_via_moneyness 用來反推 spot."""
    return Warrant(
        symbol=symbol, name=f"call_{symbol}", underlying_symbol="2330", direction="call",
        last_price=last, strike=strike, exercise_ratio=ratio,
        days_to_expiry=days, moneyness_pct=spot_implied_via_moneyness,
        volume=volume, bid_ask_spread_pct=spread,
        delta=0.5, iv_buy=40, iv_sell=41,
    )


def test_breakeven_call():
    w = _call("01", strike=2400, ratio=0.005, last=1.5)
    # BE = 2400 + 1.5 / 0.005 = 2700
    assert compute_breakeven(w) == 2700


def test_breakeven_put():
    w = _call("02", strike=2400, ratio=0.005, last=1.5)
    w.direction = "put"
    # BE = 2400 - 1.5/0.005 = 2100
    assert compute_breakeven(w) == 2100


def test_intrinsic_at_target_call():
    # spot=2250, strike=2500, ratio=0.005, last=1.0
    w = _call("03", strike=2500, ratio=0.005, last=1.0,
              spot_implied_via_moneyness=-10.0)  # 2500 × (1-0.10) = 2250
    inputs = ScenarioInputs(target_price=2800, days_to_target=60, spot_now=2250)
    r = evaluate_scenario(w, inputs)
    # intrinsic at target = (2800 - 2500) × 0.005 = 1.5
    assert r.intrinsic_at_target == pytest.approx(1.5, abs=1e-6)


def test_expected_price_at_expiration():
    # 目標日 = 到期日 → 預期權證價 = intrinsic
    w = _call("04", strike=2400, ratio=0.005, last=2.0, days=60,
              spot_implied_via_moneyness=-6.25)
    inputs = ScenarioInputs(target_price=2800, days_to_target=60, spot_now=2250)
    r = evaluate_scenario(w, inputs)
    # T_remain = 0 → 純 intrinsic = (2800-2400) × 0.005 = 2.0
    assert r.expected_warrant_price == pytest.approx(2.0, abs=1e-6)
    # 報酬 0%
    assert r.expected_return_pct == pytest.approx(0.0, abs=1e-6)


def test_expected_price_with_time_value_remaining():
    # 目標日 < 到期日 → 還有時間價值
    w = _call("05", strike=2400, ratio=0.005, last=2.0, days=120,
              spot_implied_via_moneyness=-6.25)
    inputs = ScenarioInputs(target_price=2800, days_to_target=60, spot_now=2250)
    r = evaluate_scenario(w, inputs)
    # intrinsic_now = (2250-2400 < 0) × 0.005 = 0
    # time_value_now = 2.0 - 0 = 2.0
    # T_remain = 120 - 60 = 60 → decay = sqrt(60/120) ≈ 0.7071
    # intrinsic_target = (2800-2400) × 0.005 = 2.0
    # expected_W = 2.0 + 2.0 × 0.7071 = 3.414
    assert r.expected_warrant_price == pytest.approx(3.414, abs=0.01)
    # 報酬 ≈ 70.7%
    assert r.expected_return_pct == pytest.approx(70.7, abs=0.5)


def test_evaluate_scenarios_filters_and_sorts():
    # 三檔權證：A 達標+50%, B 達標+200%, C 達標 -30%
    A = _call("A", strike=2300, ratio=0.005, last=2.0, days=120,
              spot_implied_via_moneyness=-2.17, volume=200)
    B = _call("B", strike=2600, ratio=0.005, last=0.5, days=90,
              spot_implied_via_moneyness=-13.46, volume=200)
    # C：履約 3000 太遠，達標時還是價外
    C = _call("C", strike=3000, ratio=0.005, last=0.3, days=120,
              spot_implied_via_moneyness=-25.0, volume=200)

    inputs = ScenarioInputs(target_price=2800, days_to_target=60, spot_now=2250)
    batch = evaluate_scenarios([A, B, C], inputs, require_profit_at_target=True, min_volume=50)
    # C 應被過濾（達標時 expected_return 為 0 或負）
    symbols = [r.warrant.symbol for r in batch.results]
    assert "C" not in symbols
    # 排序：B 報酬率最高應排第一
    assert batch.results[0].warrant.symbol == "B"
    assert batch.excluded_no_profit == 1


def test_alive_at_target_filter():
    # 天期 50 < 目標 60 → 應被剃除
    expired = _call("X", strike=2400, ratio=0.005, last=2.0, days=50,
                    spot_implied_via_moneyness=-6.25, volume=200)
    alive = _call("Y", strike=2400, ratio=0.005, last=2.0, days=120,
                  spot_implied_via_moneyness=-6.25, volume=200)
    inputs = ScenarioInputs(target_price=2800, days_to_target=60, spot_now=2250)
    batch = evaluate_scenarios([expired, alive], inputs, min_volume=50)
    symbols = [r.warrant.symbol for r in batch.results]
    assert "X" not in symbols
    assert "Y" in symbols
    assert batch.excluded_too_short == 1


def test_low_volume_filtered():
    w = _call("LV", strike=2400, ratio=0.005, last=1.0,
              spot_implied_via_moneyness=-6.25, volume=10, days=120)
    inputs = ScenarioInputs(target_price=2800, days_to_target=60, spot_now=2250)
    batch = evaluate_scenarios([w], inputs, min_volume=50)
    assert batch.results == []
    assert batch.excluded_low_volume == 1


def test_target_below_breakeven_warning():
    # 履約 2700、權證 1.5、行使 0.005 → BE = 2700 + 1.5/0.005 = 3000
    # 目標 2800 < BE 3000 → 應加 warning
    w = _call("BE", strike=2700, ratio=0.005, last=1.5,
              spot_implied_via_moneyness=-16.67, volume=200)
    inputs = ScenarioInputs(target_price=2800, days_to_target=60, spot_now=2250)
    r = evaluate_scenario(w, inputs)
    assert any("對也賠" in n for n in r.notes)
