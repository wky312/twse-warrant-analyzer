"""簡易 in-memory TTL cache (process 內)."""
from __future__ import annotations

import time
from typing import Any, Callable


class TTLCache:
    def __init__(self, ttl_seconds: float = 300.0) -> None:
        self.ttl = ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}

    def get_or_set(self, key: str, factory: Callable[[], Any]) -> Any:
        now = time.time()
        if key in self._store:
            ts, val = self._store[key]
            if now - ts < self.ttl:
                return val
        val = factory()
        self._store[key] = (now, val)
        return val

    def clear(self) -> None:
        self._store.clear()
