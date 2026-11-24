# ADR-004: RDS PostgreSQL + pgvector hybrid retrieval

**Status:** Accepted  
**Date:** 2026-11-24  

---

## Context

The system needs vector search plus exact token matching (maths notation, tax codes) on a lean monthly budget. Managed OpenSearch Serverless has a high floor cost relative to this portfolio footprint.

## Decision

Use **Amazon RDS PostgreSQL 16 + pgvector** (`db.t4g.micro` class in prod) as the sole retrieval store:

- Dense embeddings via Bedrock **Titan Text Embeddings V2** (1024-d).
- Hybrid retrieval: full-text search + HNSW vector search fused with **RRF** (`app/core/retrieval.py`, `app/core/rrf.py`).
- Local/CI parity via `docker compose` (`pgvector/pgvector:pg16`) and `scripts/seed_ci_corpus.py`.

Compute for the API and ingest is **ECS Fargate (ARM/Graviton)** rather than Lambda, to support SSE streaming without NAT-heavy cold-start cost trade-offs documented in the README.

## Consequences

- Schema and migrations live under `ingest/migrations/` and run on web task startup.
- Eval and Python CI stand up the same pgvector image for integration tests.
- Cost and latency claims must come from `scripts/benchmark.py` / Langfuse, not estimates alone; token prices stay in `config/prices.yaml`.
- Scaling beyond a single small RDS instance is a future ADR — do not silently introduce a second vector store.
