from __future__ import annotations

import time
from typing import Protocol

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ingest.config import USER_AGENT

RATE_LIMIT_SECONDS = 3.0
_last_request_at = 0.0


def polite_get(url: str, *, timeout: float = 60.0) -> httpx.Response:
    global _last_request_at
    elapsed = time.monotonic() - _last_request_at
    if elapsed < RATE_LIMIT_SECONDS:
        time.sleep(RATE_LIMIT_SECONDS - elapsed)
    _last_request_at = time.monotonic()

    @retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=2, max=30))
    def _get() -> httpx.Response:
        with httpx.Client(
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            timeout=timeout,
        ) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp

    return _get()


class Fetcher(Protocol):
    def fetch_markdown(self, url: str, fmt: str) -> str: ...
