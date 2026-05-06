"""CSV fetcher：讀取使用者匯出的 CSV 檔（手動方式繞過爬蟲限制）.

使用者可從券商網站或 Yahoo 手動複製權證表格 → 存成 CSV → 餵入此 fetcher.
欄位名彈性對應，缺欄位自動 None.
"""
from __future__ import annotations

import csv
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Optional

from twse_warrant.fetchers.base import BaseFetcher, FetcherError
from twse_warrant.models import Direction, Warrant


# 中英欄位別名（小寫去空白比對）
COLUMN_ALIASES: dict[str, list[str]] = {
    "symbol": ["權證代碼", "代碼", "symbol", "code"],
    "name": ["權證名稱", "名稱", "name"],
    "direction": ["認購售", "類型", "direction", "type"],
    "last_price": ["成交價", "現價", "last", "price"],
    "change": ["漲跌", "change"],
    "change_pct": ["漲跌幅%", "漲跌幅", "changepercent"],
    "volume": ["成交量", "volume"],
    "trade_count": ["成交筆數", "tradecount"],
    "bid_price": ["買價", "bid"],
    "ask_price": ["賣價", "ask"],
    "bid_ask_spread_pct": ["買賣價差比%", "買賣價差比", "spread"],
    "strike": ["履約價", "strike"],
    "exercise_ratio": ["行使比例", "exerciseratio"],
    "days_to_expiry": ["剩餘天數", "天期"],
    "issued_units": ["發行張數", "issuedunits"],
    "outstanding_units": ["流通在外張數"],
    "outstanding_pct": ["流通在外比例%", "流通在外比例"],
    "iv_buy": ["買價隱波%", "買價隱波"],
    "iv_sell": ["賣價隱波%", "賣價隱波", "成交價隱波%", "成交價隱波"],
    "delta": ["delta"],
    "theta": ["theta"],
    "gamma": ["gamma"],
    "vega": ["vega"],
    "leverage": ["實質槓桿", "槓桿"],
    "moneyness_pct": ["價內外", "價內外程度", "moneyness"],
    "issuer": ["發行券商", "券商"],
    "maturity_date": ["到期日", "maturity"],
    "option_type": ["發行型態", "型態", "option_type"],
}


def _norm_key(s: str) -> str:
    return s.replace(" ", "").replace("　", "").lower()


def _resolve_columns(headers: list[str]) -> dict[str, int]:
    """Map field name → column index."""
    norm_headers = [_norm_key(h) for h in headers]
    out: dict[str, int] = {}
    for field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            ka = _norm_key(alias)
            for i, h in enumerate(norm_headers):
                if ka == h or ka in h:
                    out[field] = i
                    break
            if field in out:
                break
    return out


def _parse_float(s: str) -> Optional[float]:
    if s is None:
        return None
    s = str(s).strip().replace(",", "").replace("%", "").replace("倍", "")
    if s in ("", "-", "N/A", "n/a", "--"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _parse_int(s: str) -> Optional[int]:
    f = _parse_float(s)
    return int(f) if f is not None else None


def _parse_direction(s: str) -> Direction:
    s = str(s or "").strip()
    if "認售" in s or "put" in s.lower():
        return "put"
    if "認購" in s or "call" in s.lower():
        return "call"
    return "call"


def _parse_date(s: str):
    if not s or s.strip() in ("-", "--"):
        return None
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


class CSVFetcher(BaseFetcher):
    name = "csv"

    def __init__(self, csv_path_or_text: str | Path) -> None:
        if isinstance(csv_path_or_text, Path) or (
            isinstance(csv_path_or_text, str) and Path(csv_path_or_text).exists()
        ):
            self.text = Path(csv_path_or_text).read_text(encoding="utf-8")
        else:
            self.text = csv_path_or_text

    def fetch(self, underlying: str, direction: Direction = "all") -> list[Warrant]:
        reader = csv.reader(StringIO(self.text))
        rows = list(reader)
        if not rows:
            raise FetcherError("CSV 是空的")
        headers = rows[0]
        col = _resolve_columns(headers)
        if "symbol" not in col:
            raise FetcherError(f"CSV 缺必要欄位「權證代碼」。已辨識欄位: {list(col.keys())}")

        out: list[Warrant] = []
        for r in rows[1:]:
            if not r or all(not c.strip() for c in r):
                continue

            def cell(field: str) -> str:
                idx = col.get(field)
                if idx is None or idx >= len(r):
                    return ""
                return r[idx]

            dirn = _parse_direction(cell("direction") or cell("name"))
            if direction != "all" and dirn != direction:
                continue

            iv_buy = _parse_float(cell("iv_buy"))
            iv_sell = _parse_float(cell("iv_sell"))

            out.append(Warrant(
                symbol=cell("symbol").strip(),
                name=cell("name").strip(),
                underlying_symbol=underlying,
                direction=dirn,
                last_price=_parse_float(cell("last_price")),
                change=_parse_float(cell("change")),
                change_pct=_parse_float(cell("change_pct")),
                volume=_parse_int(cell("volume")),
                trade_count=_parse_int(cell("trade_count")),
                bid_price=_parse_float(cell("bid_price")),
                ask_price=_parse_float(cell("ask_price")),
                bid_ask_spread_pct=_parse_float(cell("bid_ask_spread_pct")),
                strike=_parse_float(cell("strike")),
                exercise_ratio=_parse_float(cell("exercise_ratio")),
                days_to_expiry=_parse_int(cell("days_to_expiry")),
                issued_units=_parse_int(cell("issued_units")),
                outstanding_units=_parse_int(cell("outstanding_units")),
                outstanding_pct=_parse_float(cell("outstanding_pct")),
                iv_buy=iv_buy,
                iv_sell=iv_sell,
                delta=_parse_float(cell("delta")),
                theta=_parse_float(cell("theta")),
                gamma=_parse_float(cell("gamma")),
                vega=_parse_float(cell("vega")),
                leverage=_parse_float(cell("leverage")),
                moneyness_pct=_parse_float(cell("moneyness_pct")),
                issuer=cell("issuer").strip() or None,
                maturity_date=_parse_date(cell("maturity_date")),
                option_type=cell("option_type").strip() or None,
            ))
        return out
