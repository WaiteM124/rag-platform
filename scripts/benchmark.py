#!/usr/bin/env python3
"""Benchmark live /api/ask latency and cost using the Complex Systems golden set.

Writes docs/performance.md and a machine-readable JSON summary. Does not invent
numbers — only records what the live API returns.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLDEN = REPO_ROOT / "evals" / "complex-systems" / "golden.jsonl"
DEFAULT_OUT_MD = REPO_ROOT / "docs" / "performance.md"
DEFAULT_OUT_JSON = REPO_ROOT / "docs" / "performance.json"
BENCHMARK_VERSION = "1"


def percentile(values: list[float], p: float) -> float | None:
    """Inclusive nearest-rank percentile; p in [0, 100]."""
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = max(1, min(len(ordered), math.ceil(p / 100.0 * len(ordered))))
    return ordered[rank - 1]


def load_questions(path: Path, *, limit: int | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if not row.get("question"):
            continue
        rows.append(row)
        if limit is not None and len(rows) >= limit:
            break
    return rows


def git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return "unknown"


def parse_sse_done(body: str) -> dict[str, Any] | None:
    for block in body.split("\n\n"):
        line = block.strip()
        if not line.startswith("data: "):
            continue
        try:
            payload = json.loads(line[6:])
        except json.JSONDecodeError:
            continue
        if payload.get("type") == "done":
            return payload
        if payload.get("type") == "error":
            raise RuntimeError(payload.get("message") or "ask error")
    return None


def ask_once(base_url: str, collection: str, question: str, timeout: float) -> dict[str, Any]:
    url = base_url.rstrip("/") + "/api/ask"
    payload = json.dumps({"collection": collection, "question": question}).encode("utf-8")
    req = Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
        method="POST",
    )
    t0 = time.perf_counter()
    with urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
    client_ms = (time.perf_counter() - t0) * 1000.0
    done = parse_sse_done(body)
    if done is None:
        raise RuntimeError("no SSE done event in response")
    metrics = done.get("metrics") or {}
    return {
        "client_e2e_ms": round(client_ms, 3),
        "metrics": metrics,
        "latency_ms": done.get("latency_ms"),
        "cost_usd": metrics.get("cost_usd", done.get("cost_usd")),
        "cost_status": metrics.get("cost_status", done.get("cost_status")),
        "models": metrics.get("models") or {},
        "stages_ms": (metrics.get("stages_ms") or {}),
    }


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    e2e = [float(r["client_e2e_ms"]) for r in rows]
    costs = [
        float(r["cost_usd"])
        for r in rows
        if r.get("cost_usd") is not None and r.get("cost_status") != "unverified"
    ]
    stage_names = [
        "query_embedding",
        "vector_retrieval",
        "prompt_build",
        "generation",
        "output_guard",
    ]
    stages: dict[str, dict[str, float | None]] = {}
    for name in stage_names:
        vals = [
            float(r["stages_ms"][name])
            for r in rows
            if isinstance(r.get("stages_ms"), dict) and name in r["stages_ms"]
        ]
        stages[name] = {
            "p50_ms": percentile(vals, 50),
            "p95_ms": percentile(vals, 95),
            "max_ms": max(vals) if vals else None,
            "n": len(vals),
        }

    models = {}
    for r in rows:
        for k, v in (r.get("models") or {}).items():
            models.setdefault(k, v)

    return {
        "benchmark_version": BENCHMARK_VERSION,
        "n": len(rows),
        "models": models,
        "client_e2e_ms": {
            "p50": percentile(e2e, 50),
            "p95": percentile(e2e, 95),
            "max": max(e2e) if e2e else None,
        },
        "stages": stages,
        "cost_usd": {
            "mean": statistics.fmean(costs) if costs else None,
            "p95": percentile(costs, 95),
            "n_verified": len(costs),
            "n_unverified": sum(1 for r in rows if r.get("cost_status") == "unverified"),
        },
    }


def render_markdown(summary: dict[str, Any], *, base_url: str, sha: str, ts: str) -> str:
    e2e = summary["client_e2e_ms"]
    cost = summary["cost_usd"]
    models = summary.get("models") or {}
    lines = [
        "# Performance",
        "",
        f"**Status:** Measured {ts}",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Run timestamp (UTC) | {ts} |",
        f"| Commit SHA | `{sha}` |",
        f"| Sample size | {summary['n']} |",
        f"| Base URL | {base_url} |",
        f"| Answer model | `{models.get('generation', 'n/a')}` |",
        f"| Embedding model | `{models.get('embedding', 'n/a')}` |",
        "",
        "## End-to-end latency (client-side)",
        "",
        "| Metric | ms |",
        "| --- | --- |",
        f"| p50 | {_fmt(e2e.get('p50'))} |",
        f"| p95 | {_fmt(e2e.get('p95'))} |",
        f"| max | {_fmt(e2e.get('max'))} |",
        "",
        "## Per-stage latency (server-side `metrics.stages_ms`)",
        "",
        "| Stage | p50 (ms) | p95 (ms) | max (ms) |",
        "| --- | --- | --- | --- |",
    ]
    for name, stats in (summary.get("stages") or {}).items():
        lines.append(
            f"| {name} | {_fmt(stats.get('p50_ms'))} | {_fmt(stats.get('p95_ms'))} | "
            f"{_fmt(stats.get('max_ms'))} |"
        )
    lines += [
        "",
        "## Cost per query (USD)",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| mean | {_fmt_cost(cost.get('mean'))} |",
        f"| p95 | {_fmt_cost(cost.get('p95'))} |",
        f"| verified samples | {cost.get('n_verified', 0)} |",
        f"| unverified samples | {cost.get('n_unverified', 0)} |",
        "",
        "## How measured",
        "",
        "- **Client-side end-to-end:** wall clock in `scripts/benchmark.py` from request",
        "  start until the SSE `done` event is received.",
        "- **Server-side stages:** `metrics.stages_ms` returned in the SSE `done`",
        "  payload, timed with `time.perf_counter` inside the API.",
        "- Questions from `evals/complex-systems/golden.jsonl`, sequential with pause.",
        "",
    ]
    return "\n".join(lines)


def _fmt(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1f}"


def _fmt_cost(value: float | None) -> str:
    if value is None:
        return "unverified / n/a"
    return f"${value:.6f}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default="https://rag.mileswaite.net",
        help="API base URL (default: live site)",
    )
    parser.add_argument(
        "--golden",
        type=Path,
        default=DEFAULT_GOLDEN,
        help="Golden JSONL path",
    )
    parser.add_argument("--collection", default="complex-systems")
    parser.add_argument(
        "--pause",
        type=float,
        default=2.0,
        help="Seconds to sleep between questions (politeness / cost)",
    )
    parser.add_argument("--limit", type=int, default=None, help="Max questions")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load questions and print plan without calling the API",
    )
    args = parser.parse_args(argv)

    questions = load_questions(args.golden, limit=args.limit)
    if not questions:
        print("No questions loaded", file=sys.stderr)
        return 1
    if args.dry_run:
        print(f"Would ask {len(questions)} questions at {args.base_url}")
        return 0

    results: list[dict[str, Any]] = []
    for i, row in enumerate(questions, start=1):
        qid = row.get("id", i)
        question = row["question"]
        print(f"[{i}/{len(questions)}] {qid} …", flush=True)
        try:
            result = ask_once(args.base_url, args.collection, question, args.timeout)
            result["id"] = qid
            results.append(result)
            print(
                f"  client={result['client_e2e_ms']:.0f}ms "
                f"cost={result.get('cost_usd')} status={result.get('cost_status')}",
                flush=True,
            )
        except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
            print(f"  FAILED: {exc}", file=sys.stderr, flush=True)
        if i < len(questions) and args.pause > 0:
            time.sleep(args.pause)

    if not results:
        print("All requests failed", file=sys.stderr)
        return 2

    summary = summarise(results)
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    sha = git_sha()
    payload = {
        "timestamp_utc": ts,
        "commit_sha": sha,
        "base_url": args.base_url,
        "golden": str(args.golden.relative_to(REPO_ROOT)),
        "pause_s": args.pause,
        "summary": summary,
        "results": results,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.out_md.write_text(
        render_markdown(summary, base_url=args.base_url, sha=sha, ts=ts),
        encoding="utf-8",
    )

    # Job summary / console table
    e2e = summary["client_e2e_ms"]
    print("\n## Benchmark summary\n")
    print(f"| n | {summary['n']} |")
    print(f"| e2e p50 | {_fmt(e2e.get('p50'))} ms |")
    print(f"| e2e p95 | {_fmt(e2e.get('p95'))} ms |")
    print(f"| cost mean | {_fmt_cost(summary['cost_usd'].get('mean'))} |")
    for name, stats in summary["stages"].items():
        print(f"| {name} p50/p95 | {_fmt(stats.get('p50_ms'))} / {_fmt(stats.get('p95_ms'))} |")
    print(f"\nWrote {args.out_md} and {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
