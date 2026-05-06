"""元大權證網 fetcher.

POST `/eyuanta/ws/GetWarData.ashx` with form-encoded `data={JSON paramdata}`.

回傳該標的全部 call/put 權證，**含完整 Greeks/履約/到期/行使比例/流通在外/價內外/實質槓桿**.
這是目前最完整的免費資料來源.

Reference: 從 https://www.warrantwin.com.tw/eyuanta/script/WarrantSearch.min.js 反組譯出 schema.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any, Optional

from twse_warrant.fetchers.base import BaseFetcher, FetcherError
from twse_warrant.models import Direction, Warrant
from twse_warrant.utils.http import HttpClient

logger = logging.getLogger(__name__)

ENDPOINT = "https://www.warrantwin.com.tw/eyuanta/ws/GetWarData.ashx"
REFERER = "https://www.warrantwin.com.tw/eyuanta/Warrant/Search.aspx"

# FLD_WAR_TYPE: 1/2 = 認購類（含牛證），3/4 = 認售類（含熊證）
# 篩出純認購/認售（排除牛熊證）：用回傳的 'FLD_WAR_TYPE' 字串值（'認購'/'認售'/'牛證'/'熊證'）
TYPE_FILTER_CODES: dict[Direction, list[str]] = {
    "call": ["1", "2"],
    "put": ["3", "4"],
    "all": ["1", "2", "3", "4"],
}

# 完整欄位（columns 給愈多回得愈多）
ALL_COLUMNS = [
    "FLD_WAR_ID", "FLD_WAR_NM", "FLD_WAR_TYPE", "FLD_ISSUE_AGT_ID",
    "FLD_UND_ID", "FLD_UND_NM", "FLD_OBJ_TXN_PRICE",
    "FLD_WAR_UP_DN", "FLD_WAR_UP_DN_RATE", "FLD_WAR_TXN_PRICE",
    "FLD_WAR_TXN_VOLUME", "FLD_WAR_TTL_VOLUME",
    "FLD_WAR_BUY_PRICE", "FLD_WAR_BUY_VOLUME",
    "FLD_WAR_SELL_PRICE", "FLD_WAR_SELL_VOLUME",
    "FLD_DUR_START", "FLD_LAST_TXN", "FLD_DUR_END", "FLD_OPTION_TYPE",
    "FLD_N_ISSUE_UNIT", "FLD_OUT_TOT_BAL_VOL", "FLD_OUT_VOL_RATE",
    "FLD_N_STRIKE_PRC", "FLD_N_UND_CONVER",
    "FLD_PERIOD",
    "FLD_IV_CLOSE_PRICE", "FLD_IV_BUY_PRICE", "FLD_IV_SELL_PRICE",
    "FLD_DELTA", "FLD_THETA",
    "FLD_IN_OUT", "FLD_LEVERAGE", "FLD_BUY_SELL_RATE",
]

# 元大發行人代號對照（部分）
ISSUER_CODE_MAP: dict[str, str] = {
    "980": "元大", "990": "元大",
    "950": "群益",
    "910": "凱基",
    "920": "永豐",
    "940": "統一",
    "960": "富邦",
    "970": "兆豐",
    "871": "華南永昌",
    "861": "中信",
    "880": "國泰",
    "851": "玉山",
}


def _to_float(s: Any) -> Optional[float]:
    if s is None:
        return None
    s = str(s).strip()
    if s in ("", "-", "--", "N/A"):
        return None
    s = s.replace(",", "").replace("%", "")
    try:
        return float(s)
    except ValueError:
        return None


def _to_int(s: Any) -> Optional[int]:
    f = _to_float(s)
    return int(f) if f is not None else None


def _parse_yyyymmdd(s: Any) -> Optional[Any]:
    if not s:
        return None
    s = str(s).strip()
    if not s or s == "0":
        return None
    try:
        return datetime.strptime(s, "%Y%m%d").date()
    except ValueError:
        return None


# 價內外字串：'31.30%價外' → -31.30；'5.45%價內' → +5.45
_INOUT_RE = re.compile(r"(-?\d+\.?\d*)\s*%?\s*(價內|價外)?")


def _parse_in_out(s: Any) -> Optional[float]:
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    m = _INOUT_RE.search(s)
    if not m:
        return _to_float(s)
    val = float(m.group(1))
    if m.group(2) == "價外":
        return -val
    return val  # 預設視為價內（正）


def _direction_from_war_type(war_type_str: str) -> Optional[Direction]:
    """FLD_WAR_TYPE 字串：'認購'/'認售'/'牛證'/'熊證' → call/put/None（過濾掉牛熊證）."""
    if war_type_str == "認購":
        return "call"
    if war_type_str == "認售":
        return "put"
    return None  # 牛證/熊證 不算（避免使用者買到 KO 風險商品）


class YuantaFetcher(BaseFetcher):
    """元大權證網 fetcher.

    Args:
        client: 可注入 HttpClient
        page_size: 每頁筆數，預設 500
        include_bull_bear: 是否含牛/熊證，預設 False
    """

    name = "yuanta"

    def __init__(
        self,
        client: Optional[HttpClient] = None,
        page_size: int = 500,
        include_bull_bear: bool = False,
    ) -> None:
        self.client = client or HttpClient()
        self.page_size = page_size
        self.include_bull_bear = include_bull_bear

    def _build_paramdata(
        self,
        underlying: str,
        type_codes: list[str],
        page: int = 1,
    ) -> dict:
        return {
            "format": "JSON",
            "factor": {
                "columns": ALL_COLUMNS,
                "condition": [
                    {"field": "FLD_UND_ID", "values": [underlying]},
                    {"field": "FLD_WAR_TYPE", "values": type_codes},
                ],
                "orderby": {"field": "FLD_WAR_TXN_VOLUME", "sort": "DESC", "agtfirst": "980"},
            },
            "pagination": {"row": str(self.page_size), "page": str(page)},
            "callback": 1,
        }

    def _post_one_page(self, paramdata: dict) -> dict:
        headers = {
            "Referer": REFERER,
            "Origin": "https://www.warrantwin.com.tw",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
        payload = {"data": json.dumps(paramdata, ensure_ascii=False)}
        # ASHX 對 SSL cert 有時會抱怨
        resp = self.client.post(ENDPOINT, data=payload, headers=headers, verify=False)
        return resp.json()

    def fetch(self, underlying: str, direction: Direction = "all") -> list[Warrant]:
        type_codes = TYPE_FILTER_CODES[direction]
        all_results: list[dict] = []
        page = 1
        while True:
            paramdata = self._build_paramdata(underlying, type_codes, page=page)
            j = self._post_one_page(paramdata)
            if j.get("code") != "0000":
                if page == 1:
                    raise FetcherError(
                        f"元大 API 錯誤 code={j.get('code')}，標的 {underlying} 可能無權證掛牌"
                    )
                break
            results = j.get("result") or []
            all_results.extend(results)
            total_pages = int(j.get("pages") or 1)
            if page >= total_pages:
                break
            page += 1
            if page > 20:
                logger.warning("Stopped pagination after 20 pages")
                break

        if not all_results:
            raise FetcherError(f"元大 API 找不到標的 {underlying} 的 {direction} 權證")

        warrants: list[Warrant] = []
        for r in all_results:
            w = self._row_to_warrant(r, underlying)
            if w is None:
                continue
            warrants.append(w)
        return warrants

    def _row_to_warrant(self, r: dict, underlying: str) -> Warrant | None:
        war_type = (r.get("FLD_WAR_TYPE") or "").strip()
        d = _direction_from_war_type(war_type)
        if d is None:
            if not self.include_bull_bear:
                return None
            d = "call" if war_type == "牛證" else "put"

        bid = _to_float(r.get("FLD_WAR_BUY_PRICE"))
        ask = _to_float(r.get("FLD_WAR_SELL_PRICE"))
        spread_pct_raw = _to_float(r.get("FLD_BUY_SELL_RATE"))
        # FLD_BUY_SELL_RATE 元大格式為 "%" 數字，例 7.84 表 7.84%
        spread_pct = spread_pct_raw

        # 行使比例 — 元大給的是「每千單位權證可換多少標的」/1000，已是小數（0.0060）
        ratio = _to_float(r.get("FLD_N_UND_CONVER"))

        # 流通在外比例
        out_pct = _to_float(r.get("FLD_OUT_VOL_RATE"))

        return Warrant(
            symbol=(r.get("FLD_WAR_ID") or "").strip(),
            name=(r.get("FLD_WAR_NM") or "").strip(),
            underlying_symbol=(r.get("FLD_UND_ID") or underlying).strip(),
            underlying_name=(r.get("FLD_UND_NM") or "").strip(),
            direction=d,
            last_price=_to_float(r.get("FLD_WAR_TXN_PRICE")),
            change=_to_float(r.get("FLD_WAR_UP_DN")),
            change_pct=_to_float(r.get("FLD_WAR_UP_DN_RATE")),
            volume=_to_int(r.get("FLD_WAR_TXN_VOLUME")),
            trade_count=None,  # 元大此 endpoint 沒給筆數，要另一個 endpoint
            bid_price=bid,
            ask_price=ask,
            bid_ask_spread_pct=spread_pct,
            strike=_to_float(r.get("FLD_N_STRIKE_PRC")),
            exercise_ratio=ratio,
            issue_date=_parse_yyyymmdd(r.get("FLD_DUR_START")),
            last_trade_date=_parse_yyyymmdd(r.get("FLD_LAST_TXN")),
            maturity_date=_parse_yyyymmdd(r.get("FLD_DUR_END")),
            days_to_expiry=_to_int(r.get("FLD_PERIOD")),
            issued_units=_to_int(r.get("FLD_N_ISSUE_UNIT")),
            outstanding_units=_to_int(r.get("FLD_OUT_TOT_BAL_VOL")),
            outstanding_pct=out_pct,
            iv_buy=_to_float(r.get("FLD_IV_BUY_PRICE")),
            iv_sell=_to_float(r.get("FLD_IV_SELL_PRICE")),
            delta=_to_float(r.get("FLD_DELTA")),
            theta=_to_float(r.get("FLD_THETA")),
            gamma=None,
            vega=None,
            leverage=_to_float(r.get("FLD_LEVERAGE")),
            moneyness_pct=_parse_in_out(r.get("FLD_IN_OUT")),
            issuer=ISSUER_CODE_MAP.get(
                (r.get("FLD_ISSUE_AGT_ID") or "").strip(),
                (r.get("FLD_ISSUE_AGT_ID") or "").strip(),
            ),
            option_type=(r.get("FLD_OPTION_TYPE") or "").strip() or None,
        )

    def is_healthy(self) -> bool:
        return True
