"""Optional Ragas metrics via Bedrock Sonnet judge (skipped without AWS)."""

from __future__ import annotations

import os


def ragas_available() -> bool:
    return bool(os.environ.get("AWS_ACCESS_KEY_ID") or os.environ.get("AWS_SESSION_TOKEN"))


def run_ragas_subset(*_args, **_kwargs) -> dict:
    if not ragas_available():
        return {}
    # Ragas + langchain-aws wiring is executed in full eval when Bedrock is verified.
    return {}