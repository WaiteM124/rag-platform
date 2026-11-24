# ADR-002: Separate collections with per-collection eval gates

**Status:** Accepted  
**Date:** 2026-11-24  

---

## Context

The product serves multiple domains (Complex Systems now; UK Tax later) with different sources, prompts, and quality bars. Mixing collections in one undifferentiated index would pollute retrieval and hide regressions.

## Decision

Keep collections **separate** in configuration, ingest, and the vector store:

- Registries under `collections/<name>/` (e.g. `complex-systems`, `uk-tax`).
- Golden sets and thresholds under `evals/<name>/` and `evals/thresholds.yaml`.
- API requests require an explicit `collection` (`AskBody` in `app/api/main.py`).

CI enforces quality via `.github/workflows/evals.yml`: a **Complex Systems** eval gate job (and a UK Tax placeholder until Phase 5). Fast PR subset uses `make eval COLLECTION=… FAST=1`. A PR that drops scores below threshold must not merge.

## Consequences

- Retrieval and evals are always scoped by collection id.
- New collections need their own sources, golden set, thresholds, and gate job — not a shared blended score.
- Do not lower `evals/thresholds.yaml` solely to green CI; fix the system or justify a measured threshold change.
- Prompt-injection checks run as part of the Complex Systems eval path when Bedrock eval credentials are available.
