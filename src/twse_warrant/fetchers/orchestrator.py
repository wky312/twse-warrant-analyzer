"""Fetcher 鏈：依序嘗試多個來源直到取得資料."""
from __future__ import annotations

import logging
from typing import Optional

from twse_warrant.fetchers.base import BaseFetcher, FetcherError
from twse_warrant.models import Direction, Warrant

logger = logging.getLogger(__name__)


class FetcherOrchestrator:
    """嘗試 fetchers list 中的每個 fetcher，第一個成功即用."""

    def __init__(self, fetchers: list[BaseFetcher]) -> None:
        if not fetchers:
            raise ValueError("at least one fetcher is required")
        self.fetchers = fetchers

    def fetch(
        self,
        underlying: str,
        direction: Direction = "all",
    ) -> tuple[list[Warrant], str]:
        last_error: Optional[Exception] = None
        for f in self.fetchers:
            if not f.is_healthy():
                logger.info("Skip unhealthy fetcher: %s", f.name)
                continue
            try:
                data = f.fetch(underlying, direction)
                if not data:
                    raise FetcherError(f"{f.name} returned 0 warrants")
                logger.info("Used fetcher %s, got %d warrants", f.name, len(data))
                return data, f.name
            except Exception as e:
                logger.warning("Fetcher %s failed: %s", f.name, e)
                last_error = e
                continue
        raise FetcherError(
            f"All fetchers failed. Last error: {last_error}"
        )
