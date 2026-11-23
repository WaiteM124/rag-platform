# Evaluation Framework

Golden sets, metrics, gates, and injection testing for CI/CD quality gates.

## Planned Structure

```
evals/
├── datasets/
│   ├── complex-systems/golden.jsonl  # ~120 questions
│   └── uk-tax/golden.jsonl           # ~100 questions
├── injection/           # Attack prompts + poisoned-doc fixtures
├── metrics/             # Faithfulness, citation accuracy, recall@k, licence compliance
├── gates.yaml           # Thresholds per collection
└── run.py               # Writes results to Postgres + Langfuse datasets
```

## Gate Thresholds (Initial Targets)

| Metric | Gate |
|--------|------|
| Faithfulness | ≥ 0.85 |
| Citation accuracy | ≥ 0.90 |
| Answer correctness | ≥ 0.75 |
| Recall@10 (hybrid + rerank) | ≥ 0.85, ≥ vector-only |
| Abstention accuracy | ≥ 0.90 |
| Licence compliance | = 1.00 |
| Prompt-injection pass rate | ≥ 0.95 |
| p95 latency (end-to-end) | ≤ 8s |
| Cost per query (mean) | ≤ $0.005 |
| Regression vs last release | no drop > 2 pts |

Fast PR subset (~30 questions + full injection suite) gates PRs.
Full set gates deploys. Nightly runs catch drift.
