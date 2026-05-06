"""TWSE 證交所每日權證行情 fetcher.

來源：`https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&date=YYYYMMDD&type={code}`

type:
- `0999`  認購權證(不含牛證)
- `0999P` 認售權證(不含熊證)
- `0999B` 牛證
- `0999X` 熊證

回傳所有權證的當日交易（27,000+ 檔），可依「標的代號」過濾.

⚠️ 提供欄位：
  - 證券代號/名稱、成交股數、成交筆數、開盤/最高/最低/收盤、漲跌
  - 最後揭示買價/買量/賣價/賣量、本益比、標的代號/名稱/收盤價
⚠️ 不提供：履約價、行使比例、到期日、發行張數、流通在外、Delta、IV、Theta、實質槓桿
  → 這些欄位會留 None。要推薦還是要 Greeks 的話需搭配 CSV 或 Playwright fetcher.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Optional

from twse_warrant.fetchers.base import BaseFetcher, FetcherError
from twse_warrant.models import Direction, Warrant
from twse_warrant.utils.http import HttpClient

logger = logging.getLogger(__name__)

BASE_URL = "https://www.twse.com.tw/exchangeReport/MI_INDEX"


def _parse_num(s: str) -> Optional[float]:
    if s is None:
        return None
    s = str(s).strip().replace(",", "").replace("--", "").replace("&nbsp;", "")
    if not s or s in ("-", "--"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _parse_int(s: str) -> Optional[int]:
    f = _parse_num(s)
    return int(f) if f is not None else None


_TAG_RE = re.compile(r"<[^>]+>")


def _strip_tags(s: str) -> str:
    return _TAG_RE.sub("", s or "").strip()


def _parse_change_sign(html_field: str) -> str:
    """從 '<p style=color:red>+</p>' 或 '<p style=color:green>-</p>' 取出符號."""
    if not html_field:
        return ""
    text = _strip_tags(html_field)
    return text


class TWSEFetcher(BaseFetcher):
    """從證交所抓當日全市場權證並依標的過濾.

    Args:
        date: 'YYYYMMDD' 字串，預設今天
        client: 可注入 HttpClient
    """

    name = "twse"

    # 認購 = 0999, 認售 = 0999P
    _DIRECTION_TO_TYPE: dict[Direction, list[str]] = {
        "call": ["0999"],
        "put": ["0999P"],
        "all": ["0999", "0999P"],
    }

    def __init__(
        self,
        date: Optional[str] = None,
        client: Optional[HttpClient] = None,
    ) -> None:
        self.date = date or datetime.now().strftime("%Y%m%d")
        self.client = client or HttpClient()

    def fetch(self, underlying: str, direction: Direction = "all") -> list[Warrant]:
        types = self._DIRECTION_TO_TYPE[direction]
        all_rows: list[Warrant] = []
        for type_code in types:
            warrants_for_type = self._fetch_type(type_code, underlying)
            all_rows.extend(warrants_for_type)
        if not all_rows:
            raise FetcherError(
                f"TWSE 找不到標的 {underlying} 的 {direction} 權證 "
                f"(date={self.date})。可能：標的無權證掛牌、收盤資料尚未發布、或非交易日"
            )
        return all_rows

    def _fetch_type(self, type_code: str, underlying: str) -> list[Warrant]:
        params = {
            "response": "json",
            "date": self.date,
            "type": type_code,
        }
        # TWSE SSL 證書設定有時候會 fail，先停 verify
        resp = self.client.get(BASE_URL, params=params, verify=False)
        body = resp.json()
        if body.get("stat") != "OK":
            logger.warning("TWSE returned stat=%s for type=%s", body.get("stat"), type_code)
            return []

        # 真正的 warrant table 是 tables[9]（最後一張）
        tables = body.get("tables", [])
        warrant_table = None
        for t in tables:
            title = t.get("title", "")
            if "認購權證" in title or "認售權證" in title:
                warrant_table = t
                break
        if not warrant_table:
            return []

        fields: list[str] = warrant_table.get("fields", [])
        rows: list[list[str]] = warrant_table.get("data", [])

        # Build column index map
        idx = {field: i for i, field in enumerate(fields)}

        direction: Direction = "call" if "認購" in warrant_table.get("title", "") else "put"

        out: list[Warrant] = []
        for row in rows:
            try:
                target_code_raw = row[idx["標的代號"]] if "標的代號" in idx else ""
                target_code = (target_code_raw or "").strip()
                if target_code != underlying:
                    continue

                bid_price = _parse_num(row[idx["最後揭示買價"]]) if "最後揭示買價" in idx else None
                ask_price = _parse_num(row[idx["最後揭示賣價"]]) if "最後揭示賣價" in idx else None
                spread_pct = None
                if bid_price is not None and ask_price is not None and bid_price > 0:
                    mid = (bid_price + ask_price) / 2
                    if mid > 0:
                        spread_pct = (ask_price - bid_price) / mid * 100

                # 成交股數 → 張數 (1 張 = 1000 股)
                volume_shares = _parse_int(row[idx["成交股數"]]) if "成交股數" in idx else None
                volume = (volume_shares // 1000) if volume_shares is not None else None

                # 漲跌符號從 '漲跌(+/-)' html 解析
                change_sign_field = row[idx["漲跌(+/-)"]] if "漲跌(+/-)" in idx else ""
                change_sign = _parse_change_sign(change_sign_field)
                change_val = _parse_num(row[idx["漲跌價差"]]) if "漲跌價差" in idx else None
                if change_val is not None and change_sign == "-":
                    change_val = -change_val

                last_price = _parse_num(row[idx["收盤價"]]) if "收盤價" in idx else None
                prev_close = None
                if last_price is not None and change_val is not None:
                    prev_close = last_price - change_val
                change_pct = None
                if prev_close and prev_close != 0 and change_val is not None:
                    change_pct = change_val / prev_close * 100

                # 標的收盤價 → 計算 moneyness 雖無履約但可計算 implied strike
                target_close = _parse_num(row[idx["標的收盤價/指數"]]) if "標的收盤價/指數" in idx else None

                def _s(field: str) -> str:
                    if field not in idx:
                        return ""
                    v = row[idx[field]]
                    return (v or "").strip()

                w = Warrant(
                    symbol=_s("證券代號"),
                    name=_s("證券名稱"),
                    underlying_symbol=underlying,
                    underlying_name=_s("標的名稱"),
                    direction=direction,
                    last_price=last_price,
                    change=change_val,
                    change_pct=round(change_pct, 2) if change_pct is not None else None,
                    volume=volume,
                    trade_count=_parse_int(row[idx["成交筆數"]]) if "成交筆數" in idx else None,
                    bid_price=bid_price,
                    ask_price=ask_price,
                    bid_ask_spread_pct=round(spread_pct, 2) if spread_pct is not None else None,
                    # 以下 TWSE 沒有，留 None
                    strike=None,
                    exercise_ratio=None,
                    days_to_expiry=None,
                    issued_units=None,
                    outstanding_units=None,
                    outstanding_pct=None,
                    iv_buy=None,
                    iv_sell=None,
                    delta=None,
                    theta=None,
                    gamma=None,
                    vega=None,
                    leverage=None,
                    moneyness_pct=None,
                )
                out.append(w)
            except (KeyError, IndexError, TypeError) as e:
                logger.debug("Skip row due to %s: %s", type(e).__name__, e)
                continue
        return out

    def is_healthy(self) -> bool:
        return True
