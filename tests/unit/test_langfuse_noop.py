from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.api.langfuse_trace import _NoOpObservation, maybe_trace


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
