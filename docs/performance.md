# Performance

**Status:** Not yet measured.

Run `scripts/benchmark.py` (or the **Benchmark** GitHub Actions workflow) against the
live site to replace this template with p50/p95 latency and cost figures.

| Field | Value |
| --- | --- |
| Run timestamp (UTC) | Not yet measured |
| Commit SHA | Not yet measured |
| Sample size | Not yet measured |
| Base URL | https://rag.mileswaite.net |
| Answer model | Not yet measured |
| Embedding model | Not yet measured |

## End-to-end latency (client-side)

| Metric | ms |
| --- | --- |
| p50 | Not yet measured |
| p95 | Not yet measured |
| max | Not yet measured |

## Per-stage latency (server-side `metrics.stages_ms`)

| Stage | p50 (ms) | p95 (ms) | max (ms) |
| --- | --- | --- | --- |
| query_embedding | Not yet measured | Not yet measured | Not yet measured |
| vector_retrieval | Not yet measured | Not yet measured | Not yet measured |
| prompt_build | Not yet measured | Not yet measured | Not yet measured |
| generation | Not yet measured | Not yet measured | Not yet measured |
| output_guard | Not yet measured | Not yet measured | Not yet measured |

## Cost per query (USD)

| Metric | Value |
| --- | --- |
| mean | Not yet measured |
| p95 | Not yet measured |

## How measured

- **Client-side end-to-end:** wall clock in `scripts/benchmark.py` from request start
  until the SSE `done` event is received.
- **Server-side stages:** `metrics.stages_ms` returned in the SSE `done` payload,
  timed with `time.perf_counter` inside the API (embedding, hybrid retrieval,
  prompt build, Bedrock generation, licence/output guard). There is no rerank stage
  in the current code path.
- Questions are the versioned Complex Systems golden set
  (`evals/complex-systems/golden.jsonl`), asked sequentially with a polite pause.
