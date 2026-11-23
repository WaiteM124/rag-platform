from __future__ import annotations

import argparse
import json
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path

import yaml

from app.core.answer import AnswerEngine
from evals.metrics.custom import injection_suite, licence_quote_ok

ROOT = Path(__file__).resolve().parents[1]
REPORTS = Path(__file__).resolve().parent / "reports"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--collection", required=True)
    parser.add_argument("--fast", action="store_true")
    parser.add_argument("--dsn", default="")
    args = parser.parse_args()

    dsn = args.dsn or __import__("ingest.config", fromlist=["db_dsn"]).db_dsn()
    golden = Path(__file__).parent / args.collection / "golden.jsonl"
    thresholds_path = Path(__file__).parent / "thresholds.yaml"
    thresholds = yaml.safe_load(thresholds_path.read_text())["complex-systems"]

    engine = AnswerEngine(dsn)
    latencies: list[float] = []
    costs: list[float] = []
    citation_valid = 0
    licence_ok = 0
    total = 0

    for line in golden.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        if args.fast and not item.get("fast", True):
            continue
        t0 = time.perf_counter()
        result = engine.answer(item["question"], collection=args.collection)
        latencies.append(time.perf_counter() - t0)
        costs.append(result.cost_usd)
        total += 1
        if result.citations_valid:
            citation_valid += 1
        if result.licence_compliant and licence_quote_ok(result.answer, result.chunks):
            licence_ok += 1

    inj_pass, inj_total = injection_suite(engine, args.collection)
    metrics = {
        "collection": args.collection,
        "version": "v1",
        "n_questions": total,
        "citation_validity": citation_valid / total if total else 0.0,
        "licence_compliance": licence_ok / total if total else 0.0,
        "injection_pass_rate": inj_pass / inj_total if inj_total else 1.0,
        "mean_cost_usd": statistics.mean(costs) if costs else 0.0,
        "p50_latency_s": statistics.median(latencies) if latencies else 0.0,
        "p95_latency_s": (sorted(latencies)[int(0.95 * len(latencies)) - 1] if latencies else 0.0),
        "ragas_note": "Ragas Bedrock judge runs when AWS credentials are available",
        "faithfulness": None,
        "context_precision": None,
        "context_recall": None,
        "answer_relevancy": None,
    }

    gates_passed = (
        metrics["citation_validity"] >= thresholds["citation_validity"]
        and metrics["licence_compliance"] >= thresholds["licence_compliance"]
        and metrics["injection_pass_rate"] >= thresholds["injection_pass_rate"]
    )

    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    REPORTS.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS / f"{ts}.json"
    md_path = REPORTS / f"{ts}.md"
    json_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    md_path.write_text(_markdown_summary(metrics, thresholds, gates_passed), encoding="utf-8")
    print(f"Wrote {json_path} and {md_path}")
    return 0 if gates_passed else 1


def _markdown_summary(metrics: dict, thresholds: dict, passed: bool) -> str:
    return f"""# Eval report ({metrics["collection"]}) v1

- Questions: {metrics["n_questions"]}
- Citation validity: {metrics["citation_validity"]:.3f} (gate {thresholds["citation_validity"]})
- Licence compliance: {metrics["licence_compliance"]:.3f} (gate {thresholds["licence_compliance"]})
- Injection pass rate: {metrics["injection_pass_rate"]:.3f}
  (gate {thresholds["injection_pass_rate"]})
- Mean cost/query: ${metrics["mean_cost_usd"]:.6f}
- p50 latency: {metrics["p50_latency_s"]:.2f}s
- p95 latency: {metrics["p95_latency_s"]:.2f}s

Gate: {"PASS" if passed else "FAIL"}
"""


if __name__ == "__main__":
    raise SystemExit(main())
