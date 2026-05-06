"""Yahoo 奇摩股市權證 fetcher.

⚠️ 狀態：scaffold

Yahoo 個股權證頁 (`https://tw.stock.yahoo.com/quote/{id}.TW/warrant`) 是
client-side React 渲染，伺服器回傳的 HTML 是空殼。要真正抓到表格資料需要
擇一：

1. 用 Playwright/Selenium 啟瀏覽器讓 React 跑完，再從 DOM 撈資料.
2. 找到 Yahoo 內部的 GraphQL/REST endpoint（嘗試過 `_td-stock/api/resource/
   StockServices.warrants` 但回傳的是 DR/REIT 列表，不是個股權證）.

目前先以 NotImplementedError 提示。建議實作順序：

- 短期：用 CSVFetcher 餵手動匯出資料.
- 中期：用 MockFetcher 跑 UI/分析測試.
- 長期：加上 Playwright 做真實抓取（fuhwa-fund-dashboard 已有 Playwright 範例）.
"""
from __future__ import annotations

from twse_warrant.fetchers.base import BaseFetcher, FetcherError
from twse_warrant.models import Direction, Warrant


class YahooFetcher(BaseFetcher):
    name = "yahoo"

    def fetch(self, underlying: str, direction: Direction = "all") -> list[Warrant]:
        raise FetcherError(
            "YahooFetcher 尚未實作（需 Playwright 渲染 JS）。"
            "請改用 MockFetcher（demo）或 CSVFetcher（手動資料）。"
        )

    def is_healthy(self) -> bool:
        return False
