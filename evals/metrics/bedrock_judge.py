"""LLM-as-judge metrics via Bedrock Converse (DeepSeek judge by default)."""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field

from app.core.bedrock import converse
from app.core.cost import TokenUsage, load_price_cards
from evals.metrics.judge_parse import parse_judge_scores
from evals.metrics.ragas_judge import judge_model_id, ragas_available

JUDGE_SYSTEM = """You are an impartial RAG evaluation judge.
Score the answer using ONLY the provided context and reference.
Output a single JSON object with float scores from 0.0 to 1.0 for:
faithfulness, answer_relevancy, context_precision, context_recall.
No markdown, no code fences, no explanation — JSON only."""


@dataclass
class JudgeRunResult:
    scores: dict[str, float] | None = None
    parse_error: str | None = None
    usage: TokenUsage | None = None


@dataclass
class RagasAggregate:
    faithfulness: float | None = None
    answer_relevancy: float | None = None
    context_precision: float | None = None
    context_recall: float | None = None
    judge_cost_total_usd: float = 0.0
    judge_parse_failures: int = 0
    _lists: dict[str, list[float]] = field(
        default_factory=lambda: {
            k: []
            for k in (
                "faithfulness",
                "answer_relevancy",
                "context_precision",
                "context_recall",
            )
        }
    )

    def add(self, result: JudgeRunResult) -> None:
        if result.usage:
            prices = load_price_cards()
            self.judge_cost_total_usd += result.usage.cost_usd(prices)
        if result.scores:
            for key, val in result.scores.items():
                self._lists[key].append(val)
        else:
            self.judge_parse_failures += 1

    def finalize(self) -> None:
        for key, vals in self._lists.items():
            mean = statistics.mean(vals) if vals else None
            setattr(self, key, mean)


def judge_one(
    *,
    question: str,
    reference_answer: str,
    answer: str,
    context: str,
) -> JudgeRunResult:
    if not ragas_available():
        return JudgeRunResult(parse_error="bedrock_unavailable")
    model = judge_model_id()
    user_payload = {
        "question": question,
        "reference_answer": reference_answer,
        "answer": answer,
        "context": context,
    }
    text, tokens = converse(
        messages=[
            {
                "role": "user",
                "content": [{"text": json.dumps(user_payload, ensure_ascii=False)}],
            }
        ],
        system=JUDGE_SYSTEM,
        model_id=model,
        max_tokens=512,
    )
    scores, err = parse_judge_scores(text)
    usage = TokenUsage(
        input_tokens=tokens["input_tokens"],
        output_tokens=tokens["output_tokens"],
        model_id=model,
    )
    return JudgeRunResult(scores=scores, parse_error=err, usage=usage)


def empty_aggregate() -> RagasAggregate:
    agg = RagasAggregate()
    agg.finalize()
    return agg
