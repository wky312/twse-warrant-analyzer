"""Fetcher 抽象介面."""
from __future__ import annotations

from abc import ABC, abstractmethod

from twse_warrant.models import Direction, Warrant


class BaseFetcher(ABC):
    """所有資料來源實作的共用介面."""

    name: str = "base"

    @abstractmethod
    def fetch(self, underlying: str, direction: Direction = "all") -> list[Warrant]:
        """抓取指定標的的權證清單.

        Args:
            underlying: 標的代碼，例 "2330"
            direction: "call" 認購 / "put" 認售 / "all" 兩者

        Returns:
            list[Warrant]，可能為空
        """
        raise NotImplementedError

    def is_healthy(self) -> bool:
        """快速健康檢查，預設一律健康；fetcher 可覆寫."""
        return True


class FetcherError(Exception):
    """Fetcher 失敗（網路、解析、空結果）."""
