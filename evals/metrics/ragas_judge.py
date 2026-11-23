"""Ragas metrics via a cross-family Bedrock judge (skipped without AWS)."""

from __future__ import annotations

import os

from app.core.bedrock import JUDGE_MODEL


def judge_model_id() -> str:
    return os.environ.get("JUDGE_MODEL_ID") or os.environ.get("RAG_JUDGE_MODEL_ID") or JUDGE_MODEL


def ragas_available() -> bool:
    return bool(os.environ.get("AWS_ACCESS_KEY_ID") or os.environ.get("AWS_SESSION_TOKEN"))


def run_ragas_subset(*_args, **_kwargs) -> dict:
    if not ragas_available():
        return {}
    # Ragas + langchain-aws wiring uses judge_model_id() and Converse when enabled in CI.
    return {"judge_model_id": judge_model_id()}
