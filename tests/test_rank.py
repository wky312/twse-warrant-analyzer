from twse_warrant.analyzers.profiles import PROFILE_WEIGHTS
from twse_warrant.analyzers.rank import analyze_warrants, score_warrants


def test_weights_sum_to_one():
    for profile, weights in PROFILE_WEIGHTS.items():
        s = sum(weights.values())
        assert abs(s - 1.0) < 1e-9, f"{profile} weights sum to {s}, not 1.0"


def test_score_warrants_returns_sorted_descending(sample_warrants):
    # 取前三檔通過過濾的好權證
    candidates = [w for w in sample_warrants if w.symbol in ("70001A", "70002B", "70003C")]
    scored = score_warrants(candidates, "stable")
    assert len(scored) == 3
    scores = [s.total_score for s in scored]
    assert scores == sorted(scores, reverse=True)


def test_stable_prefers_low_iv(sample_warrants):
    # 70001A IV=22.5, 70002B IV=55.5, 70003C IV=38.5
    candidates = [w for w in sample_warrants if w.symbol in ("70001A", "70002B", "70003C")]
    scored = score_warrants(candidates, "stable")
    # 70001A 應該排第一
    assert scored[0].symbol == "70001A"


def test_aggressive_prefers_high_leverage(sample_warrants):
    candidates = [w for w in sample_warrants if w.symbol in ("70001A", "70002B", "70003C")]
    scored = score_warrants(candidates, "aggressive")
    # 70002B 槓桿 10 最高，應該排第一
    assert scored[0].symbol == "70002B"


def test_warnings_triggered(sample_warrants):
    # 用一檔 18 天的權證 → 應觸發近月警示（< 21）
    from datetime import date
    from twse_warrant.models import Warrant
    short = Warrant(
        symbol="70099X", name="近月", underlying_symbol="2330", direction="call",
        days_to_expiry=18, volume=100, bid_ask_spread_pct=1.0,
        iv_buy=30, iv_sell=31, delta=0.5, leverage=8.0, moneyness_pct=0,
        outstanding_pct=40,
    )
    scored = score_warrants([short], "aggressive")
    assert any("近月到期" in w for w in scored[0].warnings)


def test_analyze_warrants_full_flow(sample_warrants):
    result = analyze_warrants(
        warrants=sample_warrants,
        underlying="2330",
        direction="call",
        profiles=["stable", "aggressive"],
        top_n=3,
    )
    assert result.underlying == "2330"
    assert result.direction == "call"
    assert "stable" in result.recommendations
    assert "aggressive" in result.recommendations
    assert len(result.recommendations["stable"]) <= 3
    assert all(0 <= s.total_score <= 100 for s in result.recommendations["stable"])


def test_analyze_handles_no_warrants_for_direction():
    from datetime import date
    from twse_warrant.models import Warrant

    only_call = Warrant(
        symbol="70001", name="x", underlying_symbol="2330", direction="call",
        days_to_expiry=60, volume=100, bid_ask_spread_pct=1.0,
        iv_buy=30, iv_sell=31, delta=0.5,
    )
    result = analyze_warrants(
        warrants=[only_call],
        underlying="2330",
        direction="put",
        profiles=["stable"],
    )
    assert result.raw_count == 0
    assert any("無" in n for n in result.notes)


def test_analyze_degraded_when_all_filtered(sample_warrants):
    # 全部都太爛
    bad = [w for w in sample_warrants if w.symbol in ("70006F",)]  # 只剩量 5 的
    if not bad:
        return
    result = analyze_warrants(
        warrants=bad,
        underlying="2330",
        direction="call",
        profiles=["stable"],
    )
    assert result.degraded is True
