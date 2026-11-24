from __future__ import annotations

import logging
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from app.api.settings import get_settings

logger = logging.getLogger(__name__)


class _NoOpObservation:
    """Drop-in when Langfuse keys are absent or tracing fails."""

    def update(self, **_kwargs: Any) -> None:
        return None

    def end(self, **_kwargs: Any) -> None:
        return None

    @contextmanager
    def span(self, name: str, **_kwargs: Any) -> Iterator[_NoOpObservation]:
        yield _NoOpObservation()

    @contextmanager
    def generation(self, name: str, **_kwargs: Any) -> Iterator[_NoOpObservation]:
        yield _NoOpObservation()


class RequestTrace:
    """One Langfuse trace per request with nested stage spans / generations.

    Uses Langfuse Python SDK v2 (`trace` / `span` / `generation`). Never raises
    into the request path; flush runs in a daemon thread so SSE is not blocked.
    """

    def __init__(self, client: Any, trace: Any) -> None:
        self._client = client
        self._trace = trace

    def update(self, **kwargs: Any) -> None:
        try:
            self._trace.update(**kwargs)
        except Exception:
            logger.exception("Langfuse trace update failed")

    @contextmanager
    def span(self, name: str, **kwargs: Any) -> Iterator[Any]:
        obs: Any = _NoOpObservation()
        try:
            clean = {k: v for k, v in kwargs.items() if v is not None}
            obs = self._trace.span(name=name, **clean)
        except Exception:
            logger.exception("Langfuse span start failed name=%s", name)
            yield _NoOpObservation()
            return
        try:
            yield obs
        finally:
            try:
                obs.end()
            except Exception:
                logger.exception("Langfuse span end failed name=%s", name)

    @contextmanager
    def generation(self, name: str, **kwargs: Any) -> Iterator[Any]:
        obs: Any = _NoOpObservation()
        try:
            clean = {k: v for k, v in kwargs.items() if v is not None}
            obs = self._trace.generation(name=name, **clean)
        except Exception:
            logger.exception("Langfuse generation start failed name=%s", name)
            yield _NoOpObservation()
            return
        try:
            yield obs
        finally:
            try:
                obs.end()
            except Exception:
                logger.exception("Langfuse generation end failed name=%s", name)

    def flush_async(self) -> None:
        client = self._client

        def _flush() -> None:
            try:
                client.flush()
            except Exception:
                logger.exception("Langfuse flush failed")

        threading.Thread(target=_flush, name="langfuse-flush", daemon=True).start()


@contextmanager
def maybe_trace(
    name: str,
    metadata: dict[str, Any] | None = None,
    *,
    request_id: str | None = None,
) -> Iterator[RequestTrace | _NoOpObservation]:
    """Yield a RequestTrace when keys are set; otherwise a no-op observation."""
    settings = get_settings()
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        yield _NoOpObservation()
        return

    client = None
    try:
        from langfuse import Langfuse

        client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host or "https://cloud.langfuse.com",
        )
        meta = dict(metadata or {})
        if request_id:
            meta["request_id"] = request_id
        trace = client.trace(name=name, metadata=meta, id=request_id)
        wrapper = RequestTrace(client, trace)
        yield wrapper
        wrapper.flush_async()
    except Exception:
        logger.exception("Langfuse trace failed")
        yield _NoOpObservation()
