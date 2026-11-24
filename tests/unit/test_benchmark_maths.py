from __future__ import annotations

from scripts.benchmark import FAILURE_RATE_EXIT_THRESHOLD, percentile, summarise


def test_percentile_empty():
    assert percentile([], 50) is None


def test_percentile_single():
    assert percentile([10.0], 95) == 10.0


def test_percentile_known_set():
    vals = [10.0, 20.0, 30.0, 40.0, 50.0]
    assert percentile(vals, 50) == 30.0
    assert percentile(vals, 100) == 50.0
    assert percentile(vals, 0) == 10.0


def test_summarise_stages_cost_and_failures():
    successes = [
        {
            "client_e2e_ms": 100.0,
            "cost_usd": 0.001,
            "cost_status": "ok",
            "models": {"generation": "qwen.x", "embedding": "titan"},
            "stages_ms": {
                "query_embedding": 10.0,
                "vector_retrieval": 20.0,
                "prompt_build": 1.0,
                "generation": 60.0,
                "stream_to_client": 5.0,
                "output_guard": 2.0,
            },
        },
        {
            "client_e2e_ms": 200.0,
            "cost_usd": 0.003,
            "cost_status": "ok",
            "models": {"generation": "qwen.x", "embedding": "titan"},
            "stages_ms": {
                "query_embedding": 12.0,
                "vector_retrieval": 22.0,
                "prompt_build": 1.5,
                "generation": 150.0,
                "stream_to_client": 8.0,
                "output_guard": 2.5,
            },
        },
        {
            "client_e2e_ms": 150.0,
            "cost_usd": None,
            "cost_status": "unverified",
            "models": {"generation": "qwen.x", "embedding": "titan"},
            "stages_ms": {
                "query_embedding": 11.0,
                "vector_retrieval": 21.0,
                "prompt_build": 1.2,
                "generation": 100.0,
                "stream_to_client": 6.0,
                "output_guard": 2.2,
            },
        },
    ]
    failures = [
        {"id": "x", "ok": False, "error_type": "IncompleteRead", "error": "drop"},
        {"id": "y", "ok": False, "error_type": "IncompleteRead", "error": "drop2"},
    ]
    summary = summarise(successes, failures)
    assert summary["n"] == 3
    assert summary["n_attempted"] == 5
    assert summary["n_failed"] == 2
    assert summary["failure_rate"] == 0.4
    assert summary["failures_by_type"]["IncompleteRead"] == 2
    assert summary["client_e2e_ms"]["p50"] == 150.0
    assert summary["cost_usd"]["n_verified"] == 2
    assert summary["cost_usd"]["mean"] == 0.002
    assert summary["stages"]["generation"]["p50_ms"] == 100.0
    assert summary["stages"]["stream_to_client"]["n"] == 3
    assert FAILURE_RATE_EXIT_THRESHOLD == 0.20
