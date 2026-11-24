## Summary

<!-- What changed and why. State assumptions and out-of-scope items. -->

## Checklist

- [ ] **RAG rules respected** — public-repo secrets hygiene; no client code/data/names; licence-aware retrieval; collections stay separate; Terraform-only infra; no invented metrics; prompt-injection + output guard intact; Miles merges ([AGENTS.md](../AGENTS.md))
- [ ] **Licence guard** — `app/core/composer.py` untouched, or changes covered by tests (`tests/unit/test_composer.py` and related)
- [ ] **Eval gates** — affected collection gates still pass; thresholds in `evals/thresholds.yaml` not lowered to green CI
- [ ] **Tests added or updated** — existing tests not weakened or deleted to pass
- [ ] **Tests and lint passing** — ruff / pytest / `web` typecheck+build as relevant (existing CI green; do not add new workflows)
- [ ] **No secrets** — no API keys, credentials, private keys, Langfuse key values, or hardcoded AWS account IDs
- [ ] **Docs updated** — README / ADRs / `AGENTS.md` / `CONTRIBUTING.md` updated if behaviour or workflow changed

## Test plan

<!-- Commands run locally, or "rely on existing CI path filters". -->
