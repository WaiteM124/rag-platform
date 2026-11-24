# Architecture Decision Records

Lightweight ADRs for durable choices in this repo. Prefer reconstructing decisions from code and README over inventing rationale.

## Format

Each record is `ADR-NNN-short-title.md`:

```markdown
# ADR-NNN: Title

**Status:** Proposed | Accepted | Superseded | Deprecated
**Date:** YYYY-MM-DD

---

## Context

What problem or constraint forced a choice?

## Decision

What we chose.

## Consequences

Follow-ons, trade-offs, and what become easier or harder.
```

## Index

| ADR | Title | Status |
|---|---|---|
| [001](ADR-001-licence-aware-retrieval.md) | Licence-aware retrieval and response composer | Accepted |
| [002](ADR-002-separate-collections-eval-gates.md) | Separate collections with per-collection eval gates | Accepted |
| [003](ADR-003-terraform-only-infrastructure.md) | Terraform-only AWS infrastructure | Accepted |
| [004](ADR-004-pgvector-hybrid-retrieval.md) | RDS PostgreSQL + pgvector hybrid retrieval | Accepted |

When behaviour changes, update the relevant ADR (or supersede it) and keep `AGENTS.md` in sync.
