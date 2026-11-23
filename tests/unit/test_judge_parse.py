import pytest

from evals.metrics.judge_parse import parse_judge_scores

SAMPLE_FENCED = """Here is my assessment:
```json
{
  "faithfulness": 0.92,
  "answer_relevancy": 0.88,
  "context_precision": 0.75,
  "context_recall": 0.81
}
```
"""

SAMPLE_REASONING = """Step 1: compare claims to context.
Step 2: score relevancy.
{"faithfulness": 0.7, "answer_relevancy": 0.85, "context_precision": 0.6, "context_recall": 0.55}
"""

SAMPLE_REFUSAL = "I cannot evaluate this content because it may be harmful."

SAMPLE_THINKING = (
    "Visible<pre>not used</pre> "
    "<think>hidden chain</think>"
    '{"faithfulness": 1.0, "answer_relevancy": 0.9, '
    '"context_precision": 0.8, "context_recall": 0.7}'
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (SAMPLE_FENCED, 0.92),
        (SAMPLE_REASONING, 0.7),
        (SAMPLE_THINKING, 1.0),
    ],
)
def test_parse_judge_scores_happy_paths(raw: str, expected: float) -> None:
    scores, err = parse_judge_scores(raw)
    assert err is None
    assert scores is not None
    assert scores["faithfulness"] == expected


def test_parse_judge_refusal_not_scored_zero() -> None:
    scores, err = parse_judge_scores(SAMPLE_REFUSAL)
    assert scores is None
    assert err == "judge_refusal"


def test_parse_judge_invalid_json() -> None:
    scores, err = parse_judge_scores("{not valid json")
    assert scores is None
    assert err is not None
