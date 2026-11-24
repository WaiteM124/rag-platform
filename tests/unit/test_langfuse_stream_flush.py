from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.api.langfuse_trace import RequestTrace, reset_langfuse_client_for_tests
from app.core.retrieval import RetrievalTiming, RetrievedChunk


def test_request_trace_flush_called_once():
    client = MagicMock()
    trace = MagicMock()
    wrapper = RequestTrace(client, trace)
    wrapper.flush()
    wrapper.flush()
    client.flush.assert_called_once()


def test_streamed_ask_creates_trace_spans_generation_and_flushes():
    """SSE ask path must create nested observations and flush after the stream."""
    reset_langfuse_client_for_tests()

    fake_client = MagicMock()
    fake_trace = MagicMock()
    fake_span = MagicMock()
    fake_gen = MagicMock()
    fake_client.trace.return_value = fake_trace
    fake_trace.span.return_value = fake_span
    fake_trace.generation.return_value = fake_gen

    chunk = RetrievedChunk(
        chunk_id=1,
        source_id="cs-018",
        text="Early warnings include variance.",
        score=1.0,
        rank=1,
        licence_class="A",
        attribution_text="Dakos",
        source_url="https://example.com",
        title="Dakos",
    )
    prices = {
        "qwen.qwen3-235b-a22b-2507-v1:0": {
            "input_per_1k": 0.00034,
            "output_per_1k": 0.00137,
            "verified": True,
        },
        "amazon.titan-embed-text-v2:0": {
            "input_per_1k": 0.0001,
            "output_per_1k": 0.0,
            "verified": True,
        },
    }

    def fake_stream(*_a, **_k):
        def gen():
            yield "Answer [1]"

        return gen(), {"input_tokens": 10, "output_tokens": 5}

    with (
        patch("app.api.main.run_migrations"),
        patch("app.api.main.spend_cap_exceeded", return_value=False),
        patch("app.api.main.rate_limited", return_value=False),
        patch("app.api.main.converse_stream", side_effect=fake_stream),
        patch("app.api.main.AnswerEngine") as mock_engine_cls,
        patch("app.api.main.record_spend_gbp"),
        patch("app.api.main.emit_daily_spend_gbp"),
        patch("app.api.main.load_price_cards", return_value=prices),
        patch("app.api.main.LicenceComposer") as comp_cls,
        patch("app.api.langfuse_trace.get_langfuse_client", return_value=fake_client),
        patch("app.api.langfuse_trace.get_settings") as gs,
        patch("app.api.langfuse_trace.langfuse_keys_configured", return_value=True),
    ):
        gs.return_value.langfuse_public_key = "pk-test"
        gs.return_value.langfuse_secret_key = "sk-test"
        gs.return_value.langfuse_host = "https://cloud.langfuse.com"
        gs.return_value.answer_model_id = "qwen.qwen3-235b-a22b-2507-v1:0"
        gs.return_value.usd_to_gbp = 0.79
        gs.return_value.question_max_chars = 1000
        gs.return_value.daily_spend_cap_gbp = 2.0

        engine = mock_engine_cls.return_value
        engine.retriever.retrieve.return_value = [chunk]
        engine.retriever._last_embed_input_tokens = 7
        engine.retriever._last_embed_model_id = "amazon.titan-embed-text-v2:0"
        engine.retriever._last_timing = RetrievalTiming(
            query_embedding_ms=11.0, vector_retrieval_ms=22.0
        )
        engine.composer.context_blocks.return_value = "<context>data</context>"
        comp_cls.return_value.apply_output_policy.return_value = ("Answer [1]", True)

        from app.api.main import app

        client = TestClient(app)
        r = client.post(
            "/api/ask",
            json={"collection": "complex-systems", "question": "What is a tipping point?"},
        )

    assert r.status_code == 200
    assert "done" in r.text
    fake_client.trace.assert_called()
    assert fake_trace.span.call_count >= 1
    assert fake_trace.generation.call_count >= 1
    fake_client.flush.assert_called()
    # Spans/generations should be ended
    assert fake_span.end.call_count >= 1
    assert fake_gen.end.call_count >= 1
