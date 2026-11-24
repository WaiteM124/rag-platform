from __future__ import annotations

import json

from app.api.request_log import build_metrics_log_line, privacy_hash


def test_privacy_hash_stable_and_short():
    h = privacy_hash("What is a tipping point?")
    assert len(h) == 16
    assert h == privacy_hash("What is a tipping point?")
    assert h != privacy_hash("other")


def test_metrics_log_line_shape_no_question_text():
    line = build_metrics_log_line(
        request_id="req-1",
        collection="complex-systems",
        question="secret question text",
        answer_len=42,
        models={"embedding": "amazon.titan-embed-text-v2:0", "generation": "qwen.x"},
        stages_ms={"query_embedding": 12.5, "generation": 900.0},
        total_ms=1000.0,
        tokens={"embed_input": 8, "generation_input": 100, "generation_output": 50},
        cost_usd=0.001,
        cost_status="ok",
    )
    raw = json.dumps(line)
    assert "secret question text" not in raw
    assert line["event"] == "rag_request_metrics"
    assert line["request_id"] == "req-1"
    assert line["collection"] == "complex-systems"
    assert line["question_hash"] == privacy_hash("secret question text")
    assert line["question_len"] == len("secret question text")
    assert line["answer_len"] == 42
    assert line["stages_ms"]["generation"] == 900.0
    assert line["tokens"]["generation_input"] == 100
    assert line["cost_usd"] == 0.001
    assert line["cost_status"] == "ok"
    assert "models" in line
