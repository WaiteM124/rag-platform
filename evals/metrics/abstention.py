from __future__ import annotations

from evals.metrics.custom import REFUSAL_PATTERNS


def is_abstention_answer(text: str) -> bool:
    if not text or not text.strip():
        return True
    lowered = text.lower()
    if REFUSAL_PATTERNS.search(text):
        return True
    phrases = (
        "do not know",
        "don't know",
        "not in the context",
        "insufficient context",
        "cannot answer",
        "can't answer",
        "no information",
    )
    return any(p in lowered for p in phrases)


def abstention_correct(*, expected_abstain: bool, answer: str) -> bool:
    abstained = is_abstention_answer(answer)
    return abstained if expected_abstain else not abstained
