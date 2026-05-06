"""Pytest fixture：合成 Warrant 清單."""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from twse_warrant.models import Warrant


def _make(symbol: str, **kw) -> Warrant:
    base = dict(
        symbol=symbol,
        name=f"權證{symbol}",
        underlying_symbol="2330",
        direction="call",
        last_price=2.0,
        change=0.05,
        change_pct=2.5,
        volume=200,
        trade_count=80,
        bid_price=1.99,
        ask_price=2.01,
        bid_ask_spread_pct=1.0,
        strike=1100.0,
        exercise_ratio=0.005,
        days_to_expiry=90,
        issued_units=5000,
        outstanding_units=2500,
        outstanding_pct=50.0,
        iv_buy=40.0,
        iv_sell=41.0,
        delta=0.5,
        theta=-0.005,
        gamma=0.001,
        vega=0.02,
        leverage=5.0,
        moneyness_pct=0.0,
        issuer="元大",
        maturity_date=date(2026, 8, 1),
    )
    base.update(kw)
    return Warrant(**base)


@pytest.fixture
def sample_warrants() -> list[Warrant]:
    """8 檔合成 call warrants，分數差異化."""
    return [
        # 0: 穩健型優等生（低 IV、窄價差、中天期、高量）
        _make("70001A", iv_buy=22, iv_sell=23, days_to_expiry=80, volume=2000,
              bid_ask_spread_pct=0.6, leverage=4.5, delta=0.5, outstanding_pct=30,
              trade_count=600),
        # 1: 進攻型優等生（高槓桿、高 Delta、短天期、高量）
        _make("70002B", iv_buy=55, iv_sell=56, days_to_expiry=40, volume=3000,
              bid_ask_spread_pct=0.8, leverage=10.0, delta=0.75, moneyness_pct=3.0,
              outstanding_pct=40, trade_count=900),
        # 2: 平庸（兩個 profile 都中段）
        _make("70003C", iv_buy=38, iv_sell=39, days_to_expiry=60, volume=300,
              bid_ask_spread_pct=1.5, leverage=6.0, delta=0.5, outstanding_pct=55,
              trade_count=120),
        # 3: 應被穩健型過濾掉（IV 過高 81）
        _make("70004D", iv_buy=80, iv_sell=82, days_to_expiry=60, volume=500,
              bid_ask_spread_pct=1.5, leverage=6.0, delta=0.6, outstanding_pct=55),
        # 4: 應被穩健型過濾掉（剩餘天數 25 < 30）
        _make("70005E", iv_buy=35, iv_sell=36, days_to_expiry=25, volume=500,
              bid_ask_spread_pct=1.5, leverage=6.0, delta=0.55, outstanding_pct=55),
        # 5: 應被全部過濾掉（成交量 5）
        _make("70006F", iv_buy=35, iv_sell=36, days_to_expiry=60, volume=5,
              bid_ask_spread_pct=1.5, leverage=6.0, delta=0.55, outstanding_pct=55,
              trade_count=2),
        # 6: 應被穩健型過濾（價差 4% > 3%）
        _make("70007G", iv_buy=35, iv_sell=36, days_to_expiry=60, volume=500,
              bid_ask_spread_pct=4.0, leverage=6.0, delta=0.55, outstanding_pct=55),
        # 7: 缺 Delta，必排除
        _make("70008H", delta=None, iv_buy=35, iv_sell=36, days_to_expiry=60, volume=500),
    ]
