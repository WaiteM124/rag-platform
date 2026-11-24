from __future__ import annotations

import logging
import sys

_CONFIGURED = False


def configure_app_logging() -> None:
    """Ensure ``app.*`` (and ``rag.*``) INFO logs reach stdout / CloudWatch.

    Uvicorn leaves the root logger at WARNING by default, so ``logger.info``
    from application modules is otherwise silent. Call once at process startup
    before any startup status lines (e.g. Langfuse auth).
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    formatter = logging.Formatter("%(levelname)s:%(name)s:%(message)s")
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)

    for name in ("app", "rag"):
        log = logging.getLogger(name)
        log.setLevel(logging.INFO)
        # Avoid duplicate handlers if startup is invoked more than once in tests.
        if not any(
            isinstance(h, logging.StreamHandler) and getattr(h, "stream", None) is sys.stdout
            for h in log.handlers
        ):
            log.addHandler(handler)
        log.propagate = False

    _CONFIGURED = True


def reset_app_logging_for_tests() -> None:
    """Test helper: allow configure_app_logging to run again."""
    global _CONFIGURED
    _CONFIGURED = False
