from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any

from app.api.settings import get_settings

logger = logging.getLogger(__name__)


@contextmanager
def maybe_trace(name: str, metadata: dict[str, Any] | None = None):
    settings = get_settings()
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        yield None
        return
    try:
        from langfuse import Langfuse

        client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
        trace = client.trace(name=name, metadata=metadata or {})
        yield trace
        client.flush()
    except Exception:
        logger.exception("Langfuse trace failed")
        yield None