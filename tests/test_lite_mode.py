"""驗證 lite mode：缺 Greeks 時也能跑出推薦."""
from twse_warrant.analyzers.filters import apply_filters, detect_lite_mode
from twse_warrant.analyzers.rank import analyze_warrants
from twse_warrant.models import Warrant


def _twse_like_warrant(symbol: str, volume: int, spread: float, last: float = 1.0):
    """模擬 TWSE 抓回的 warrant：缺 Greeks/履約/到期/流通比."""
    return Warrant(
        symbol=symbol, name=f"權證{symbol}", underlying_symbol="2330", direction="call",
        last_price=last, volume=volume, trade_count=int(volume * 0.4),
        bid_price=last - 0.01, ask_price=last + 0.01,
        bid_ask_spread_pct=spread,
        # Greeks/履約/到期 全 None（TWSE 沒這些）
        delta=None, iv_buy=None, iv_sell=None, leverage=None,
        days_to_expiry=None, strike=None, exercise_ratio=None,
        moneyness_pct=None, outstanding_pct=None,
    )


def test_detect_lite_mode():
    twse_like = [_twse_like_warrant(f"0{i}", 100, 1.0) for i in range(5)]
    assert detect_lite_mode(twse_like) is True

    full_data = [
        Warrant(
            symbol=f"0{i}", name="x", underlying_symbol="2330", direction="call",
            volume=100, bid_ask_spread_pct=1.0,
            delta=0.5, iv_buy=30, iv_sell=31, days_to_expiry=60,
        )
        for i in range(5)
    ]
    assert detect_lite_mode(full_data) is False


def test_lite_mode_filter_skips_greeks():
    """TWSE-like 資料應通過 filter（不再被 Greeks 缺失擋掉）."""
    twse_like = [
        _twse_like_warrant("01", volume=200, spread=1.0),  # 應通過
        _twse_like_warrant("02", volume=10, spread=1.0),   # 量太少
        _twse_like_warrant("03", volume=200, spread=8.0),  # 價差太寬
    ]
    passed, excluded, lite = apply_filters(twse_like, "stable")
    assert lite is True
    assert excluded == 0  # lite mode 不算 Greeks 排除
    symbols = {w.symbol for w in passed}
    assert symbols == {"01"}


def test_lite_mode_full_pipeline():
    twse_like = [_twse_like_warrant(f"0{i:02d}", volume=100 + i * 50, spread=1.5) for i in range(10)]
    result = analyze_warrants(
        warrants=twse_like,
        underlying="2330",
        direction="call",
        profiles=["stable", "aggressive"],
        top_n=3,
    )
    assert any("lite 模式" in n for n in result.notes)
    assert "stable" in result.recommendations
    assert "aggressive" in result.recommendations
    # 高量者排前面（因為 lite 主要看 volume + spread）
    assert result.recommendations["stable"][0].warrant.symbol == "009"
