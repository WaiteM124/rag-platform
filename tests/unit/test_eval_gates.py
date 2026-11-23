import math

from evals.run import evaluate_gates


def test_gates_skip_ragas_when_judge_disabled() -> None:
    metrics = {
        "faithfulness": None,
        "citation_validity": 1.0,
        "licence_compliance": 1.0,
        "injection_pass_rate": 1.0,
    }
    thresholds = {
        "faithfulness": 0.85,
        "citation_validity": 1.0,
        "licence_compliance": 1.0,
        "injection_pass_rate": 1.0,
    }
    ok, failing = evaluate_gates(metrics, thresholds, judge_enabled=False)
    assert ok
    assert failing == []


def test_gates_fail_ragas_none_when_judge_enabled() -> None:
    metrics = {
        "faithfulness": None,
        "answer_relevancy": 0.9,
        "context_precision": 0.9,
        "context_recall": 0.9,
        "citation_validity": 1.0,
        "licence_compliance": 1.0,
        "injection_pass_rate": 1.0,
    }
    thresholds = {
        "faithfulness": 0.85,
        "answer_relevancy": 0.8,
        "context_precision": 0.7,
        "context_recall": 0.7,
        "citation_validity": 1.0,
        "licence_compliance": 1.0,
        "injection_pass_rate": 1.0,
    }
    ok, failing = evaluate_gates(metrics, thresholds, judge_enabled=True)
    assert not ok
    assert "faithfulness" in failing


def test_gates_nan_treated_as_missing() -> None:
    metrics = {
        "faithfulness": math.nan,
        "answer_relevancy": 0.9,
        "context_precision": 0.9,
        "context_recall": 0.9,
        "citation_validity": 1.0,
        "licence_compliance": 1.0,
        "injection_pass_rate": 1.0,
    }
    thresholds = {
        "faithfulness": 0.85,
        "answer_relevancy": 0.8,
        "context_precision": 0.7,
        "context_recall": 0.7,
        "citation_validity": 1.0,
        "licence_compliance": 1.0,
        "injection_pass_rate": 1.0,
    }
    ok, failing = evaluate_gates(metrics, thresholds, judge_enabled=True)
    assert not ok
    assert "faithfulness" in failing