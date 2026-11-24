from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger("rag.metrics")


def privacy_hash(text: str) -> str:
    """Short SHA-256 prefix — never log question/answer content."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def emit_request_metrics_log(payload: dict[str, Any]) -> None:
    """One structured JSON line to stdout (CloudWatch) per ask request."""
    line = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    # Use print so the line is always on stdout even if logging is misconfigured.
    print(line, flush=True)
    logger.info("request_metrics %s", line)


def build_metrics_log_line(
    *,
    request_id: str,
    collection: str,
    question: str,
    answer_len: int,
    models: dict[str, str],
    stages_ms: dict[str, float],
    total_ms: float,
    tokens: dict[str, int],
    cost_usd: float | None,
    cost_status: str,
) -> dict[str, Any]:
    return {
        "event": "rag_request_metrics",
        "request_id": request_id,
        "collection": collection,
        "question_hash": privacy_hash(question),
        "question_len": len(question),
        "answer_len": answer_len,
        "models": models,
        "stages_ms": stages_ms,
        "total_ms": total_ms,
        "tokens": tokens,
        "cost_usd": cost_usd,
        "cost_status": cost_status,
    }
