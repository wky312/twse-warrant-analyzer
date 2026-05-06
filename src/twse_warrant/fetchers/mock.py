"""合成樣本資料 fetcher，方便 demo 與測試 UI/分析鏈."""
from __future__ import annotations

import random
from datetime import date, timedelta

from twse_warrant.fetchers.base import BaseFetcher
from twse_warrant.models import Direction, Warrant


class MockFetcher(BaseFetcher):
    """產生符合台股權證命名與數值合理範圍的合成資料."""

    name = "mock"

    def __init__(self, count: int = 30, seed: int | None = 42) -> None:
        self.count = count
        self.seed = seed

    def fetch(self, underlying: str, direction: Direction = "all") -> list[Warrant]:
        rng = random.Random(self.seed)
        # Simulate underlying spot price by hash of symbol
        if underlying == "2330":
            spot, name = 1100.0, "台積電"
        elif underlying == "2454":
            spot, name = 1500.0, "聯發科"
        elif underlying == "2317":
            spot, name = 200.0, "鴻海"
        elif underlying == "2330":
            spot, name = 1100.0, "台積電"
        else:
            spot, name = 100.0 + (hash(underlying) % 500), f"標的{underlying}"

        out: list[Warrant] = []
        for i in range(self.count):
            d: Direction = rng.choice(["call", "put"])
            if direction != "all" and d != direction:
                continue

            days = rng.choice([18, 35, 60, 90, 120, 180])
            # Strike near spot, with offset
            offset_pct = rng.uniform(-0.18, 0.18)
            strike = round(spot * (1 + offset_pct), 0)

            moneyness = (spot - strike) / spot * 100  # for call: positive = ITM
            if d == "put":
                moneyness = -moneyness

            iv_buy = round(rng.uniform(20, 70), 2)
            iv_sell = round(iv_buy + rng.uniform(0.1, 1.5), 2)
            delta_mag = max(0.05, min(0.95, 0.5 + moneyness / 100 * 1.5))
            delta = delta_mag if d == "call" else -delta_mag

            volume = int(rng.choice([5, 15, 50, 200, 800, 2500]))
            spread_pct = round(rng.uniform(0.3, 4.5), 2)
            outstanding_pct = round(rng.uniform(5, 95), 1)
            leverage = round(rng.uniform(1.5, 12.0), 2)
            last = round(rng.uniform(0.3, 8.0), 2)
            bid = round(last - last * spread_pct / 200, 2)
            ask = round(last + last * spread_pct / 200, 2)
            change = round(rng.uniform(-0.5, 0.5), 2)
            change_pct = round(change / max(last, 0.01) * 100, 2)
            issuer = rng.choice(["元大", "群益", "凱基", "永豐", "統一"])
            issue_d = date(2026, 5, 6) - timedelta(days=rng.randint(20, 200))

            out.append(Warrant(
                symbol=f"{rng.randint(70000, 99999):05d}{rng.choice(list('ABCDEF'))}",
                name=f"{issuer}{underlying}{'購' if d=='call' else '售'}{i:02d}",
                underlying_symbol=underlying,
                underlying_name=name,
                direction=d,
                last_price=last,
                change=change,
                change_pct=change_pct,
                volume=volume,
                trade_count=int(volume * rng.uniform(0.3, 1.2)),
                bid_price=bid,
                ask_price=ask,
                bid_ask_spread_pct=spread_pct,
                strike=strike,
                exercise_ratio=round(rng.uniform(0.001, 0.05), 4),
                issue_date=issue_d,
                last_trade_date=issue_d + timedelta(days=days - 4),
                maturity_date=issue_d + timedelta(days=days),
                days_to_expiry=days,
                issued_units=5000,
                outstanding_units=int(5000 * outstanding_pct / 100),
                outstanding_pct=outstanding_pct,
                iv_buy=iv_buy,
                iv_sell=iv_sell,
                delta=round(delta, 4),
                theta=round(-rng.uniform(0.001, 0.02), 4),
                gamma=round(rng.uniform(0.0001, 0.005), 5),
                vega=round(rng.uniform(0.001, 0.05), 4),
                leverage=leverage,
                moneyness_pct=round(moneyness, 2),
                issuer=issuer,
                option_type=rng.choice(["歐式", "美式"]),
            ))
        return out
