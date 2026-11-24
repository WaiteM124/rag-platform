from __future__ import annotations

import logging
import sys
from unittest.mock import MagicMock, patch

from app.api.logging_config import configure_app_logging, reset_app_logging_for_tests


def test_configure_app_logging_enables_info_on_stdout():
    reset_app_logging_for_tests()
    # Drop any leftover handlers from prior tests.
    for name in ("app", "app.api.langfuse_trace", "rag"):
        log = logging.getLogger(name)
        log.handlers.clear()
        log.setLevel(logging.NOTSET)

    configure_app_logging()
    configure_app_logging()  # idempotent

    app_log = logging.getLogger("app")
    assert app_log.level == logging.INFO
    assert app_log.propagate is False
    stdout_handlers = [
        h
        for h in app_log.handlers
        if isinstance(h, logging.StreamHandler) and getattr(h, "stream", None) is sys.stdout
    ]
    assert len(stdout_handlers) == 1
    assert stdout_handlers[0].level == logging.INFO

    child = logging.getLogger("app.api.langfuse_trace")
    # Child inherits effective level from parent when NOTSET.
    assert child.getEffectiveLevel() == logging.INFO


def test_langfuse_startup_info_reaches_stdout(capsys):
    """With app logging configured, the auth-ok INFO line appears on stdout."""
    reset_app_logging_for_tests()
    for name in ("app", "app.api.langfuse_trace"):
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).setLevel(logging.NOTSET)
    configure_app_logging()

    from app.api.langfuse_trace import init_langfuse_at_startup, reset_langfuse_client_for_tests

    reset_langfuse_client_for_tests()
    with patch("app.api.langfuse_trace.get_settings") as gs:
        gs.return_value.langfuse_public_key = "pk-abcdef012345"
        gs.return_value.langfuse_secret_key = "sk-secret"
        gs.return_value.langfuse_host = "https://cloud.langfuse.com"
        client = MagicMock()
        client.auth_check.return_value = True
        with patch("app.api.langfuse_trace.get_langfuse_client", return_value=client):
            init_langfuse_at_startup()

    out = capsys.readouterr().out
    assert "Langfuse auth ok" in out
    assert "pk-abcde" in out
    assert "sk-secret" not in out
