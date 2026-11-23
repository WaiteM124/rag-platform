from __future__ import annotations

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from botocore.exceptions import ClientError
from pgvector import Vector
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_delay,
    wait_random_exponential,
)

from ingest.config import bedrock_runtime

DEFAULT_MODEL = os.environ.get("RAG_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
DIMENSIONS = 1024
EMBED_MAX_RPS = float(os.environ.get("EMBED_MAX_RPS", "2"))
EMBED_MAX_CONCURRENCY = max(1, int(os.environ.get("EMBED_MAX_CONCURRENCY", "1")))


class EmbeddingThrottledError(Exception):
    """Raised when Bedrock embedding is still throttled after client retries."""


class _EmbedStats:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.calls = 0
        self.throttle_retries = 0

    def record_call(self) -> None:
        with self._lock:
            self.calls += 1

    def record_throttle_retry(self) -> None:
        with self._lock:
            self.throttle_retries += 1

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return {"calls": self.calls, "throttle_retries": self.throttle_retries}

    def reset(self) -> None:
        with self._lock:
            self.calls = 0
            self.throttle_retries = 0


_stats = _EmbedStats()


def get_embed_stats() -> dict[str, int]:
    return _stats.snapshot()


def reset_embed_stats() -> None:
    _stats.reset()


class _RateLimiter:
    def __init__(self, max_rps: float) -> None:
        self._min_interval = 1.0 / max_rps if max_rps > 0 else 0.0
        self._lock = threading.Lock()
        self._next_allowed = 0.0

    def acquire(self) -> None:
        if self._min_interval <= 0:
            return
        with self._lock:
            now = time.monotonic()
            wait = self._next_allowed - now
            if wait > 0:
                time.sleep(wait)
                now = time.monotonic()
            self._next_allowed = now + self._min_interval


_rate_limiter = _RateLimiter(EMBED_MAX_RPS)


def to_vector(values: list[float]) -> Vector:
    return Vector(values)


def _is_throttling(exc: BaseException) -> bool:
    if isinstance(exc, ClientError):
        code = exc.response.get("Error", {}).get("Code", "")
        return code in ("ThrottlingException", "TooManyRequestsException")
    return False


def _on_throttle_retry(retry_state) -> None:
    _stats.record_throttle_retry()


@retry(
    retry=retry_if_exception(_is_throttling),
    wait=wait_random_exponential(multiplier=1, max=30),
    stop=stop_after_delay(120),
    before_sleep=_on_throttle_retry,
    reraise=True,
)
def _invoke_model(client, model_id: str, body: str):
    _stats.record_call()
    return client.invoke_model(modelId=model_id, body=body)


def _embed_one(text: str, model_id: str) -> list[float]:
    _rate_limiter.acquire()
    client = bedrock_runtime()
    body = json.dumps({"inputText": text[:25000], "dimensions": DIMENSIONS})
    try:
        resp = _invoke_model(client, model_id, body)
    except ClientError as exc:
        if _is_throttling(exc):
            raise EmbeddingThrottledError(f"Bedrock throttled after retries: {exc}") from exc
        raise
    payload = json.loads(resp["body"].read())
    emb = payload.get("embedding") or payload.get("embeddingsByType", {}).get("float")
    if not emb:
        raise RuntimeError(f"Unexpected embedding response keys: {payload.keys()}")
    return emb


def embed_texts(texts: list[str], model_id: str | None = None) -> list[list[float]]:
    model_id = model_id or DEFAULT_MODEL
    if not texts:
        return []
    if EMBED_MAX_CONCURRENCY == 1:
        return [_embed_one(text, model_id) for text in texts]

    results: list[list[float] | None] = [None] * len(texts)
    with ThreadPoolExecutor(max_workers=EMBED_MAX_CONCURRENCY) as pool:
        futures = {pool.submit(_embed_one, text, model_id): idx for idx, text in enumerate(texts)}
        for future in as_completed(futures):
            idx = futures[future]
            results[idx] = future.result()
    return [results[i] for i in range(len(texts))]  # type: ignore[misc]
