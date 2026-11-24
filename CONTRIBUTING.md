# Contributing

Short human guide. Agents and detailed RAG rules: see [AGENTS.md](AGENTS.md).

## Setup

**Prerequisites:** Python 3.12+, pip, Docker (Postgres + pgvector); optional Node.js 20+ (`web/`); Terraform ≥ 1.10 and tflint for infra work.

```bash
pip install -e ".[dev]"
pre-commit install
docker compose up -d
export DATABASE_URL=postgresql://rag:raglocal@localhost:5432/ragplatform
python -m ingest.migrations.runner
python scripts/seed_ci_corpus.py
```

Frontend:

```bash
cd web
npm install
npm run dev
```

## Running

```bash
uvicorn app.api.main:app --reload --port 8000
# or full stack image: docker build -t rag-platform . && docker run --rm -p 8000:8000 ...
```

## Tests, lint, and eval

```bash
ruff check .
ruff format --check .
pytest -q tests/unit tests/integration tests/api tests/ingest
cd web && npm run typecheck && npm run build

make eval COLLECTION=complex-systems FAST=1
```

Eval thresholds live in `evals/thresholds.yaml`. Do not lower them to pass CI.

## Existing CI

Do **not** add lint, test, or eval workflows. The repo already has:

| Workflow | When it runs |
|---|---|
| `python.yml` | Python / tests / `web` changes — ruff, pytest, frontend typecheck+build |
| `evals.yml` | App / ingest / evals / collections changes — **per-collection eval gates** |
| `terraform.yml` | `terraform/**` changes — fmt, validate, tflint, plan/apply |
| `deploy.yml` | After successful Terraform on `main`, or manual dispatch |
| `ingest.yml`, `eval-live.yml`, `benchmark.yml` | Manual `workflow_dispatch` only |

Path filters matter: avoid edits under `terraform/**` unless you intend to run Terraform (and potentially Deploy Web on merge).

## Branch and PR conventions

- Branch from `main` with a short, descriptive name.
- Keep PRs **small and focused** on one concern.
- Fill in the pull request template checklist.
- State assumptions, concurrent work, and follow-ups in the description.
- Respect RAG rules in `AGENTS.md`: licence guard untouched or tested; eval gates passing; no secrets; no client names/data; no invented metrics.
- Do not delete or weaken tests or eval thresholds solely to make CI pass.
- Do not merge or trigger deploy/ingest/eval-live/benchmark workflows without Miles's go-ahead.

## Definition of done

- RAG rules in `AGENTS.md` respected (public-repo secrets hygiene; licence-aware retrieval; separate collections; Terraform-only infra; honest metrics; injection/output guards)
- Tests added/updated and passing; lint clean; eval gates green for affected collections
- No secrets, keys, or hardcoded AWS account IDs in the change
- Docs updated when behaviour or workflow changes
- Existing CI green on the PR
