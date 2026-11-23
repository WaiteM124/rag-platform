from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from app.core.answer import AnswerEngine
from app.core.bedrock import ANSWER_MODEL, JUDGE_MODEL
from evals.metrics.abstention import abstention_correct
from evals.metrics.bedrock_judge import empty_aggregate, judge_one
from evals.metrics.custom import injection_suite, licence_quote_ok
from evals.metrics.ragas_judge import ragas_available

ROOT = Path(__file__).resolve().parents[1]
REPORTS = Path(__file__).resolve().parent / "reports"

RAGAS_KEYS = ("faithfulness", "answer_relevancy", "context_precision", "context_recall")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--collection", required=True)
    parser.add_argument("--fast", action="store_true")
    parser.add_argument("--dsn", default="")
    parser.add_argument(
        "--golden",
        default="golden.jsonl",
        help="Golden set filename under evals/<collection>/ (e.g. golden_live.jsonl)",
    )
    args = parser.parse_args(argv)

    dsn = args.dsn or __import__("ingest.config", fromlist=["db_dsn"]).db_dsn()
    golden = Path(__file__).parent / args.collection / args.golden
    thresholds_path = Path(__file__).parent / "thresholds.yaml"
    thresholds = yaml.safe_load(thresholds_path.read_text(encoding="utf-8"))[args.collection]

    engine = AnswerEngine(dsn)
    price_cards = engine.prices
    latencies_ms: list[float] = []
    query_costs: list[float | None] = []
    citation_valid = 0
    licence_ok = 0
    abstention_hits = 0
    abstention_total = 0
    total = 0
    ragas_agg = empty_aggregate()
    judge_enabled = ragas_available()

    for line in golden.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        if args.fast and not item.get("fast", True):
            continue
        expected_abstain = not item.get("expected_source_ids")

        t0 = time.perf_counter()
        result = engine.answer(item["question"], collection=args.collection)
        latencies_ms.append((time.perf_counter() - t0) * 1000.0)

        q_cost = _query_cost(result, price_cards)
        query_costs.append(q_cost)

        if expected_abstain:
            abstention_total += 1
            if abstention_correct(expected_abstain=True, answer=result.answer):
                abstention_hits += 1
        else:
            total += 1
            if result.citations_valid:
                citation_valid += 1
            if result.licence_compliant and licence_quote_ok(result.answer, result.chunks):
                licence_ok += 1
            if judge_enabled and item.get("reference_answer"):
                ctx = "\n\n".join(c.text for c in result.chunks)
                jr = judge_one(
                    question=item["question"],
                    reference_answer=item["reference_answer"],
                    answer=result.answer,
                    context=ctx,
                )
                ragas_agg.add(jr)

    ragas_agg.finalize()
    inj_pass, inj_total = injection_suite(engine, args.collection)

    metrics: dict[str, Any] = {
        "collection": args.collection,
        "golden_file": args.golden,
        "version": "v1",
        "n_questions": total,
        "n_abstention": abstention_total,
        "answer_model": ANSWER_MODEL,
        "judge_model": JUDGE_MODEL,
        "citation_validity": citation_valid / total if total else 0.0,
        "licence_compliance": licence_ok / total if total else 0.0,
        "injection_pass_rate": inj_pass / inj_total if inj_total else 1.0,
        "abstention_accuracy": (abstention_hits / abstention_total if abstention_total else None),
        "faithfulness": ragas_agg.faithfulness,
        "answer_relevancy": ragas_agg.answer_relevancy,
        "context_precision": ragas_agg.context_precision,
        "context_recall": ragas_agg.context_recall,
        "judge_parse_failures": ragas_agg.judge_parse_failures,
        "judge_cost_total_usd": ragas_agg.judge_cost_total_usd,
        "cost_per_query_usd": _mean_nullable(query_costs),
        "p50_latency_ms": statistics.median(latencies_ms) if latencies_ms else 0.0,
        "p95_latency_ms": (
            sorted(latencies_ms)[max(0, int(0.95 * len(latencies_ms)) - 1)] if latencies_ms else 0.0
        ),
        "judge_enabled": judge_enabled,
    }

    gates_passed, failing = evaluate_gates(metrics, thresholds, judge_enabled)

    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    REPORTS.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS / f"{ts}.json"
    md_path = REPORTS / f"{ts}.md"
    metrics["gate"] = "PASS" if gates_passed else "FAIL"
    metrics["failing"] = failing
    json_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    md_text = _markdown_summary(metrics, thresholds, gates_passed, failing)
    md_path.write_text(md_text, encoding="utf-8")
    print(f"Wrote {json_path} and {md_path}")
    print(_eval_summary_line(metrics, failing, gates_passed))
    return 0 if gates_passed else 1


def evaluate_gates(
    metrics: dict[str, Any], thresholds: dict[str, float], judge_enabled: bool
) -> tuple[bool, list[str]]:
    failing: list[str] = []
    for key, min_val in thresholds.items():
        val = metrics.get(key)
        if key in RAGAS_KEYS and not judge_enabled:
            continue
        if key in RAGAS_KEYS and judge_enabled and val is None:
            failing.append(key)
            continue
        if val is None or (isinstance(val, float) and math.isnan(val)):
            failing.append(key)
            continue
        if float(val) < float(min_val):
            failing.append(key)
    return (len(failing) == 0, failing)


def _query_cost(result, price_cards: dict) -> float | None:
    return result.query_cost_usd(price_cards)


def _mean_nullable(values: list[float | None]) -> float | None:
    nums = [v for v in values if v is not None]
    if not nums:
        return None
    if any(v is None for v in values):
        return None
    return statistics.mean(nums)


def _fmt_num(val: Any) -> str:
    if val is None:
        return "null"
    if isinstance(val, float):
        return f"{val:.4f}"
    return str(val)


def _eval_summary_line(metrics: dict, failing: list[str], passed: bool) -> str:
    fail_csv = ",".join(failing) if failing else ""
    return (
        "EVAL SUMMARY "
        f"collection={metrics['collection']} "
        f"n={metrics['n_questions']} "
        f"answer_model={metrics['answer_model']} "
        f"judge_model={metrics['judge_model']} "
        f"faithfulness={_fmt_num(metrics.get('faithfulness'))} "
        f"answer_relevancy={_fmt_num(metrics.get('answer_relevancy'))} "
        f"context_precision={_fmt_num(metrics.get('context_precision'))} "
        f"context_recall={_fmt_num(metrics.get('context_recall'))} "
        f"citation_validity={_fmt_num(metrics.get('citation_validity'))} "
        f"licence_compliance={_fmt_num(metrics.get('licence_compliance'))} "
        f"injection_pass_rate={_fmt_num(metrics.get('injection_pass_rate'))} "
        f"abstention_accuracy={_fmt_num(metrics.get('abstention_accuracy'))} "
        f"p50_ms={metrics.get('p50_latency_ms', 0):.1f} "
        f"p95_ms={metrics.get('p95_latency_ms', 0):.1f} "
        f"cost_per_query_usd={_fmt_num(metrics.get('cost_per_query_usd'))} "
        f"judge_cost_total_usd={_fmt_num(metrics.get('judge_cost_total_usd'))} "
        f"judge_parse_failures={metrics.get('judge_parse_failures', 0)} "
        f"gate={'PASS' if passed else 'FAIL'} "
        f"failing=[{fail_csv}]"
    )


def _markdown_summary(metrics: dict, thresholds: dict, passed: bool, failing: list[str]) -> str:
    gate_metrics = [
        ("faithfulness", metrics.get("faithfulness")),
        ("answer_relevancy", metrics.get("answer_relevancy")),
        ("context_precision", metrics.get("context_precision")),
        ("context_recall", metrics.get("context_recall")),
        ("citation_validity", metrics.get("citation_validity")),
        ("licence_compliance", metrics.get("licence_compliance")),
        ("injection_pass_rate", metrics.get("injection_pass_rate")),
    ]
    lines = [
        f"# Eval report ({metrics['collection']}) v1",
        "",
        f"- Golden file: `{metrics.get('golden_file', 'golden.jsonl')}`",
        f"- Questions (answerable): {metrics['n_questions']}",
        f"- Abstention cases: {metrics.get('n_abstention', 0)}",
        f"- Answer model: `{metrics.get('answer_model')}`",
        f"- Judge model: `{metrics.get('judge_model')}`",
        "",
    ]
    for name, val in gate_metrics:
        thr = thresholds.get(name)
        if thr is None:
            continue
        lines.append(f"- {name}: {_fmt_num(val)} (gate {thr})")
    lines.extend(
        [
            f"- abstention_accuracy: {_fmt_num(metrics.get('abstention_accuracy'))}",
            f"- cost_per_query_usd: {_fmt_num(metrics.get('cost_per_query_usd'))}",
            f"- judge_cost_total_usd: {_fmt_num(metrics.get('judge_cost_total_usd'))}",
            f"- judge_parse_failures: {metrics.get('judge_parse_failures', 0)}",
            f"- p50 latency: {metrics.get('p50_latency_ms', 0):.1f} ms",
            f"- p95 latency: {metrics.get('p95_latency_ms', 0):.1f} ms",
            "",
            f"Gate: **{'PASS' if passed else 'FAIL'}**",
        ]
    )
    if failing:
        lines.append(f"- Failing: `{', '.join(failing)}`")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
