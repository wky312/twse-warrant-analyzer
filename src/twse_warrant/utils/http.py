"""共用 HTTP session + retry."""
from __future__ import annotations

import time
from typing import Optional

import requests

DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class HttpClient:
    """簡易封裝：UA、timeout、retry with backoff."""

    def __init__(
        self,
        ua: str = DEFAULT_UA,
        timeout: float = 15.0,
        max_retries: int = 3,
        backoff: float = 1.5,
    ) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": ua})
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff = backoff

    def get(self, url: str, params: Optional[dict] = None, **kw) -> requests.Response:
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout, **kw)
                if resp.status_code >= 500:
                    raise requests.HTTPError(f"{resp.status_code} from {url}")
                resp.raise_for_status()
                return resp
            except (requests.RequestException, requests.HTTPError) as e:
                last_exc = e
                if attempt < self.max_retries - 1:
                    time.sleep(self.backoff ** attempt)
        raise RuntimeError(f"GET {url} failed after {self.max_retries} retries: {last_exc}")

    def post(self, url: str, data=None, **kw) -> requests.Response:
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                resp = self.session.post(url, data=data, timeout=self.timeout, **kw)
                if resp.status_code >= 500:
                    raise requests.HTTPError(f"{resp.status_code} from {url}")
                resp.raise_for_status()
                return resp
            except (requests.RequestException, requests.HTTPError) as e:
                last_exc = e
                if attempt < self.max_retries - 1:
                    time.sleep(self.backoff ** attempt)
        raise RuntimeError(f"POST {url} failed after {self.max_retries} retries: {last_exc}")
