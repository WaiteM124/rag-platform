from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

from app.api.langfuse_trace import _NoOpObservation, maybe_trace
from app.api.settings import (
    get_settings,
    langfuse_keys_configured,
    normalize_langfuse_key,
    warn_langfuse_placeholder_once,
)


def test_normalize_langfuse_key_treats_blank_and_placeholder_as_absent():
    assert normalize_langfuse_key(None) == ""
    assert normalize_langfuse_key("") == ""
    assert normalize_langfuse_key("   ") == ""
    assert normalize_langfuse_key("REPLACE_ME") == ""
    assert normalize_langfuse_key("replace_me") == ""
    assert normalize_langfuse_key("  Replace_Me  ") == ""
    assert normalize_langfuse_key("pk-lf-real") == "pk-lf-real"


def test_langfuse_keys_configured_requires_both_real_keys():
    assert not langfuse_keys_configured("REPLACE_ME", "REPLACE_ME")
    assert not langfuse_keys_configured("pk-real", "REPLACE_ME")
    assert not langfuse_keys_configured("", "sk-real")
    assert langfuse_keys_configured("pk-real", "sk-real")


def test_get_settings_strips_placeholder(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "REPLACE_ME")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", " replace_me ")
    try:
        settings = get_settings()
        assert settings.langfuse_public_key == ""
        assert settings.langfuse_secret_key == ""
        assert settings.langfuse_enabled is False
    finally:
        get_settings.cache_clear()


def test_warn_langfuse_placeholder_once(caplog):
    with caplog.at_level(logging.WARNING, logger="app.api.settings"):
        warn_langfuse_placeholder_once("REPLACE_ME", "sk-real")
    assert any("placeholder" in r.message.lower() for r in caplog.records)


def test_maybe_trace_noop_without_keys():
    with patch("app.api.langfuse_trace.get_settings") as gs:
        gs.return_value.langfuse_public_key = ""
        gs.return_value.langfuse_secret_key = ""
        with maybe_trace("ask", {"collection": "complex-systems"}) as trace:
            assert isinstance(trace, _NoOpObservation)
            with trace.span("retrieval") as span:
                span.update(output={"n": 1})
            with trace.generation(name="generation", model="x") as gen:
                gen.update(usage={"input": 1})


def test_maybe_trace_noop_on_terraform_placeholder():
    with patch("app.api.langfuse_trace.get_settings") as gs:
        gs.return_value.langfuse_public_key = "REPLACE_ME"
        gs.return_value.langfuse_secret_key = "REPLACE_ME"
        fake_mod = MagicMock()
        with patch.dict("sys.modules", {"langfuse": fake_mod}):
            with maybe_trace("ask") as trace:
                assert isinstance(trace, _NoOpObservation)
        fake_mod.Langfuse.assert_not_called()


def test_maybe_trace_noop_when_client_raises():
    with patch("app.api.langfuse_trace.get_settings") as gs:
        gs.return_value.langfuse_public_key = "pk"
        gs.return_value.langfuse_secret_key = "sk"
        gs.return_value.langfuse_host = "https://cloud.langfuse.com"
        fake_mod = MagicMock()
        fake_mod.Langfuse.side_effect = RuntimeError("boom")
        with patch.dict("sys.modules", {"langfuse": fake_mod}):
            with maybe_trace("ask") as trace:
                assert isinstance(trace, _NoOpObservation)
