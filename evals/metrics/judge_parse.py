"""Parse structured judge scores from Bedrock model text (fences, reasoning, prose)."""

from __future__ import annotations

import json
import re
from typing import Any

from app.core.bedrock import strip_thinking_text

_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
_JSON_OBJECT_RE = re.compile(r"\{[\s\S]*\}")
_SCORE_KEYS = (
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
)


def parse_judge_scores(text: str) -> tuple[dict[str, float] | None, str | None]:
    """Return (scores dict, parse_error). On failure scores is None; never default to zero."""
    cleaned = strip_thinking_text(text or "").strip()
    if not cleaned:
        return None, "empty_judge_output"

    refusal = re.search(
        r"(?i)\b(i cannot|i can't|unable to (evaluate|score|judge)|won't score|refuse)",
        cleaned,
    )
    if refusal and not _JSON_OBJECT_RE.search(cleaned):
        return None, "judge_refusal"

    candidates: list[str] = []
    for block in _FENCE_RE.findall(cleaned):
        candidates.append(block.strip())
    mobj = _JSON_OBJECT_RE.search(cleaned)
    if mobj:
        candidates.append(mobj.group(0))

    last_err: str | None = None
    for raw in candidates:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            last_err = f"json_decode:{exc.msg}"
            continue
        scores = _normalize_score_object(data)
        if scores is not None:
            return scores, None
        last_err = "missing_or_invalid_score_keys"

    return None, last_err or "no_json_found"


def _normalize_score_object(data: Any) -> dict[str, float] | None:
    if not isinstance(data, dict):
        return None
    out: dict[str, float] = {}
    for key in _SCORE_KEYS:
        if key not in data:
            continue
        val = data[key]
        try:
            score = float(val)
        except (TypeError, ValueError):
            return None
        if score != score:  # NaN
            return None
        out[key] = max(0.0, min(1.0, score))
    if not out:
        return None
    return out
