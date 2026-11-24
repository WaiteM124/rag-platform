from __future__ import annotations

import logging
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from app.api.settings import get_settings, langfuse_keys_configured

logger = logging.getLogger(__name__)

_client_lock = threading.Lock()
_client: Any | None = None
_client_init_attempted = False


class _NoOpObservation:
    """Drop-in when Langfuse keys are absent or tracing fails."""

    def update(self, **_kwargs: Any) -> None:
        return None

    def end(self, **_kwargs: Any) -> None:
        return None

    def flush(self) -> None:
        return None

    def flush_async(self) -> None:
        return None

    @contextmanager
    def span(self, name: str, **_kwargs: Any) -> Iterator[_NoOpObservation]:
        yield _NoOpObservation()

    @contextmanager
    def generation(self, name: str, **_kwargs: Any) -> Iterator[_NoOpObservation]:
        yield _NoOpObservation()


def _configure_langfuse_logging() -> None:
    """Route the langfuse SDK logger to WARNING on stdout (once)."""
    lf_logger = logging.getLogger("langfuse")
    if getattr(lf_logger, "_rag_platform_configured", False):
        return
    lf_logger.setLevel(logging.WARNING)
    if not lf_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.WARNING)
        handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
        lf_logger.addHandler(handler)
    lf_logger.propagate = False
    lf_logger._rag_platform_configured = True  # type: ignore[attr-defined]


def get_langfuse_client() -> Any | None:
    """Process-wide Langfuse client (v2). None when keys absent or init failed."""
    global _client, _client_init_attempted
    settings = get_settings()
    if not langfuse_keys_configured(settings.langfuse_public_key, settings.langfuse_secret_key):
        return None
    with _client_lock:
        if _client is not None:
            return _client
        if _client_init_attempted and _client is None:
            return None
        _client_init_attempted = True
        _configure_langfuse_logging()
        try:
            from langfuse import Langfuse

            _client = Langfuse(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_host or "https://cloud.langfuse.com",
            )
            return _client
        except Exception:
            logger.exception("Langfuse client init failed")
            _client = None
            return None


def reset_langfuse_client_for_tests() -> None:
    """Test helper: drop the singleton so the next call re-initialises."""
    global _client, _client_init_attempted
    with _client_lock:
        _client = None
        _client_init_attempted = False


def init_langfuse_at_startup() -> None:
    """Call once at process start: auth_check + one clear log line (no key values)."""
    settings = get_settings()
    host = settings.langfuse_host or "https://cloud.langfuse.com"
    if not langfuse_keys_configured(settings.langfuse_public_key, settings.langfuse_secret_key):
        logger.info("Langfuse tracing disabled (keys absent or placeholder)")
        return

    _configure_langfuse_logging()
    prefix = (settings.langfuse_public_key or "")[:8]
    client = get_langfuse_client()
    if client is None:
        logger.error(
            "Langfuse auth FAILED host=%s public_key_prefix=%s reason=client_init_failed",
            host,
            prefix,
        )
        return
    try:
        ok = client.auth_check()
        if ok is False:
            logger.error(
                "Langfuse auth FAILED host=%s public_key_prefix=%s "
                "reason=auth_check_returned_false",
                host,
                prefix,
            )
            return
        logger.info(
            "Langfuse auth ok host=%s public_key_prefix=%s",
            host,
            prefix,
        )
    except Exception as exc:
        logger.error(
            "Langfuse auth FAILED host=%s public_key_prefix=%s reason=%s",
            host,
            prefix,
            f"{type(exc).__name__}: {exc}",
        )


class RequestTrace:
    """One Langfuse trace per request with nested stage spans / generations.

    Uses Langfuse Python SDK v2 (`trace` / `span` / `generation`). Never raises
    into the request path. Call ``flush()`` after the SSE stream finishes so
    observations are not lost when the generator is collected.
    """

    def __init__(self, client: Any, trace: Any) -> None:
        self._client = client
        self._trace = trace
        self._flushed = False

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

    def flush(self) -> None:
        """Flush on the request thread after the SSE stream ends."""
        if self._flushed:
            return
        self._flushed = True
        try:
            self._client.flush()
        except Exception:
            logger.exception("Langfuse flush failed")

    def flush_async(self) -> None:
        """Backward-compatible: flush in a daemon thread (prefer ``flush``)."""
        if self._flushed:
            return
        self._flushed = True
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
    """Yield a RequestTrace when keys are set; otherwise a no-op observation.

    Always flushes in ``finally`` after the ``with`` body (including after an
    SSE generator finishes), so observations are not lost to GC.
    """
    settings = get_settings()
    if not langfuse_keys_configured(settings.langfuse_public_key, settings.langfuse_secret_key):
        yield _NoOpObservation()
        return

    wrapper: RequestTrace | None = None
    try:
        client = get_langfuse_client()
        if client is None:
            yield _NoOpObservation()
            return
        meta = dict(metadata or {})
        if request_id:
            meta["request_id"] = request_id
        trace = client.trace(name=name, metadata=meta, id=request_id)
        wrapper = RequestTrace(client, trace)
        yield wrapper
    except Exception:
        logger.exception("Langfuse trace failed")
        if wrapper is None:
            # Init failed before the body ran — hand the caller a no-op.
            yield _NoOpObservation()
        else:
            # Body raised after yield; keep propagating after flush in finally.
            raise
    finally:
        if wrapper is not None:
            wrapper.flush()
