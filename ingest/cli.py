from __future__ import annotations

import argparse
import logging
from pathlib import Path

from ingest.pipeline import ingest_collection

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="rag-platform ingest")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run_p = sub.add_parser("run", help="Run ingestion for a collection")
    run_p.add_argument("--collection", required=True)
    run_p.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if args.cmd == "run":
        root = Path(__file__).resolve().parents[1]
        sources = root / "collections" / args.collection / "sources.yaml"
        if not sources.exists():
            raise SystemExit(f"Missing {sources}")
        count = ingest_collection(args.collection, sources_path=sources, limit=args.limit)
        logger.info("Ingested %s sources", count)
        return 0
    return 1
