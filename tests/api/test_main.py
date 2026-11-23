from __future__ import annotations

import importlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.main import app, resolve_static_file
from app.core.retrieval import RetrievedChunk

REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX_HTML = REPO_ROOT / "web" / "index.html"

# Minimal 1x1 PNG
_MIN_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
    b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


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
        "qwen.qwen3-235b-a22b-2507-v1:0": {"input_per_1k": 0.00034, "output_per_1k": 0.00137}
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


def test_index_html_has_absolute_og_and_twitter_meta():
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'property="og:image" content="https://rag.mileswaite.net/og-image.png"' in html
    assert 'name="twitter:card" content="summary_large_image"' in html
    assert 'name="twitter:image" content="https://rag.mileswaite.net/og-image.png"' in html


def test_resolve_static_file_rejects_traversal(tmp_path: Path):
    (tmp_path / "safe.png").write_bytes(_MIN_PNG)
    assert resolve_static_file(tmp_path, "safe.png") == (tmp_path / "safe.png").resolve()
    assert resolve_static_file(tmp_path, "../safe.png") is None
    assert resolve_static_file(tmp_path, "missing.png") is None


def test_static_catch_all_serves_png_with_image_content_type(tmp_path: Path, monkeypatch):
    (tmp_path / "index.html").write_text("<!doctype html><title>spa</title>", encoding="utf-8")
    (tmp_path / "og-image.png").write_bytes(_MIN_PNG)
    monkeypatch.setenv("STATIC_DIR", str(tmp_path))
    import app.api.main as main_mod

    importlib.reload(main_mod)
    try:
        with patch("app.api.main.run_migrations"):
            client = TestClient(main_mod.app)
            r = client.get("/og-image.png")
        assert r.status_code == 200
        assert "image/png" in r.headers["content-type"]
        assert r.content.startswith(b"\x89PNG")
        assert b"<!doctype html>" not in r.content
    finally:
        monkeypatch.delenv("STATIC_DIR", raising=False)
        importlib.reload(main_mod)
