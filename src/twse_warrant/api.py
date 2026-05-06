"""對外公開 API: analyze()."""
from __future__ import annotations

from typing import Optional, Sequence

from twse_warrant.analyzers.filters import FilterThresholds
from twse_warrant.analyzers.rank import analyze_warrants
from twse_warrant.fetchers.base import BaseFetcher
from twse_warrant.fetchers.mock import MockFetcher
from twse_warrant.fetchers.orchestrator import FetcherOrchestrator
from twse_warrant.fetchers.yuanta import YuantaFetcher
from twse_warrant.models import AnalysisResult, Direction, Profile


def analyze(
    underlying: str,
    direction: Direction = "call",
    profiles: Sequence[Profile] = ("stable", "aggressive"),
    *,
    fetchers: Optional[list[BaseFetcher]] = None,
    top_n: int = 5,
    overrides: Optional[dict[Profile, FilterThresholds]] = None,
) -> AnalysisResult:
    """主入口.

    Args:
        underlying: 標的個股代碼，例 "2330"
        direction: "call" / "put" / "all"
        profiles: 要評分的 profile 清單，預設兩個都跑
        fetchers: 自訂 fetcher 順序，預設 [MockFetcher()]（可在生產環境改成
                  [CSVFetcher(path), YahooFetcher(), ...]）
        top_n: 每個 profile 推薦前 N 名
        overrides: 過濾閾值覆寫
    """
    if fetchers is None:
        # 預設：Yuanta 含完整 Greeks → fallback Mock（離線情境）
        fetchers = [YuantaFetcher(), MockFetcher()]
    orch = FetcherOrchestrator(fetchers)
    warrants, source = orch.fetch(underlying, direction)
    return analyze_warrants(
        warrants=warrants,
        underlying=underlying,
        direction=direction,
        profiles=list(profiles),
        top_n=top_n,
        overrides=overrides,
        fetch_source=source,
    )
