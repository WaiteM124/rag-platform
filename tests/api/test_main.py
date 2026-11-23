from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.core.retrieval import RetrievedChunk


@pytest.fixture
def client():
    with patch("app.api.main.run_migrations"):
        yield TestClient(app)


def test_healthz(client):
    assert client.get("/healthz").json()["status"] == "ok"


@patch("app.api.main.psycopg.connect")
def test_readyz_ok(mock_connect, client):
    conn = MagicMock()
    mock_connect.return_value.__enter__.return_value = conn
    assert client.get("/readyz").status_code == 200


@patch("app.api.main.spend_cap_exceeded", return_value=False)
@patch("app.api.main.rate_limited", return_value=False)
@patch("app.api.main.converse_stream")
@patch("app.api.main.AnswerEngine")
def test_ask_sse(mock_engine_cls, mock_stream, _rl, _cap, client):
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
    engine = mock_engine_cls.return_value
    engine.retriever.retrieve.return_value = [chunk]
    engine.composer.context_blocks.return_value = "<context>data</context>"
    engine.prices = {
        "eu.anthropic.claude-haiku-5-5": {"input_per_1k": 0.001, "output_per_1k": 0.005}
    }

    def fake_stream(*_a, **_k):
        def gen():
            yield "Answer [1]"

        return gen(), {"input_tokens": 10, "output_tokens": 5}

    mock_stream.side_effect = fake_stream

    with patch("app.api.main.record_spend_gbp"), patch("app.api.main.emit_daily_spend_gbp"):
        with patch("app.api.main.LicenceComposer") as comp_cls:
            comp_cls.return_value.apply_output_policy.return_value = ("Answer [1]", True)
            r = client.post(
                "/api/ask",
                json={"collection": "complex-systems", "question": "What is a tipping point?"},
            )
    assert r.status_code == 200
    body = r.text
    assert "data:" in body
    assert "done" in body or "Answer" in body


def test_ask_rejects_collection(client):
    r = client.post("/api/ask", json={"collection": "uk-tax", "question": "VAT?"})
    assert r.status_code == 400