from __future__ import annotations

import argparse
import logging
from pathlib import Path

from ingest.pipeline import ingest_collection

logger = logging.getLogger(__name__)


def _eval_runner_argv(args: argparse.Namespace) -> list[str]:
    out: list[str] = ["--collection", args.collection, "--golden", args.golden]
    if args.fast:
        out.append("--fast")
    if args.require_judge:
        out.append("--require-judge")
    if args.dsn:
        out.extend(["--dsn", args.dsn])
    if args.eval_extra:
        out.extend(args.eval_extra)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="rag-platform ingest")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run_p = sub.add_parser("run", help="Run ingestion for a collection")
    run_p.add_argument("--collection", required=True)
    run_p.add_argument("--limit", type=int, default=None)

    eval_p = sub.add_parser("eval", help="Run eval harness (forwards to evals/run.py)")
    eval_p.add_argument("--collection", required=True)
    eval_p.add_argument(
        "--golden",
        default="golden.jsonl",
        help="Golden file under evals/<collection>/",
    )
    eval_p.add_argument("--fast", action="store_true")
    eval_p.add_argument(
        "--require-judge",
        action="store_true",
        help="Fail if Bedrock judge credentials are unavailable",
    )
    eval_p.add_argument(
        "--dsn",
        default="",
        help="Optional Postgres DSN (default: ingest.config.db_dsn())",
    )
    eval_p.add_argument(
        "eval_extra",
        nargs=argparse.REMAINDER,
        help="Extra args forwarded to evals/run.py",
    )

    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if args.cmd == "run":
        root = Path(__file__).resolve().parents[1]
        sources = root / "collections" / args.collection / "sources.yaml"
        if not sources.exists():
            raise SystemExit(f"Missing {sources}")
        summary = ingest_collection(args.collection, sources_path=sources, limit=args.limit)
        return summary.exit_code()
    if args.cmd == "eval":
        from evals.run import main as eval_main

        return eval_main(_eval_runner_argv(args))
    return 1
