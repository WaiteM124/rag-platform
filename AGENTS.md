# AGENTS.md — RAG Platform contributor & agent guide

Single source of truth for humans and AI agents (including Cursor) working in this repository.

**Product:** Multi-collection RAG platform on AWS — licence-aware retrieval, eval-gated CI/CD, Terraform-only infra, tracing, and measured cost/latency.

**Owner:** Miles Waite (AI systems architect). Public portfolio demo at `rag.mileswaite.net`.

**This repo is public.** Treat every commit as world-readable.

---

## Repository map

| Path | Role |
|---|---|
| `app/` | FastAPI web service (`app.api.main:app`) and RAG core library |
| `app/api/` | HTTP API, SSE `/api/ask`, rate limits, spend cap, Langfuse, metrics logging |
| `app/core/` | Retrieval (hybrid FTS + HNSW + RRF), Bedrock Converse, answer engine, **licence composer** |
| `ingest/` | Fetchers (arXiv / PDF / HTML), chunking, Titan embeddings, migrations, CLI |
| `evals/` | Golden sets per collection, Ragas/Bedrock judge, injection suite, thresholds, reports |
| `collections/` | Per-collection source registries (`complex-systems/`, `uk-tax/`) with licence metadata |
| `config/` | `models.yaml`, `prices.yaml` (Bedrock token prices — verified against AWS Price List) |
| `web/` | React + TypeScript + Vite + Tailwind SPA (built into container static assets) |
| `scripts/` | `seed_ci_corpus.py`, `benchmark.py`, golden-set helpers |
| `terraform/bootstrap/` | One-time CloudShell setup (S3 state, GitHub OIDC, IAM roles, Budget) |
| `terraform/envs/prod/` | Production environment (RDS, ECS, ALB, secrets wiring) |
| `terraform/modules/` | Reusable modules (e.g. `network/`) |
| `tests/` | `unit/`, `integration/`, `api/`, `ingest/` |
| `docs/` | Build plan, source lists, phase notes, ADRs under `docs/decisions/` |
| `.github/workflows/` | Existing CI/CD (do **not** add lint/test/eval workflows) |

Stack: **Python 3.12+**, FastAPI, Pydantic v2, psycopg3, pgvector, boto3 / Bedrock, Ragas, Langfuse; **Node 20** for `web/` (Vite + React 18 + Tailwind). Region: **eu-west-2**.

---

## Non-negotiable RAG rules

1. **Public repo — no secrets.** Never commit secrets, API keys, private keys, or hardcoded AWS account IDs. Never log Langfuse or other key values. Secrets live in **AWS Secrets Manager**, wired through Terraform.
2. **No client material.** Never use client code or data, and never name client systems or projects.
3. **Licence-aware retrieval.** Every chunk carries a licence class. Full text is republished only for open licences (OGL, CC BY, and similar Class A; Class B while non-commercial). **Class C** gets short capped excerpts (≤300 chars) plus a link out. The composer in `app/core/composer.py` must not be weakened or bypassed; changes need tests (`tests/unit/test_composer.py` and related).
4. **Collections stay separate.** UK Tax and Complex Systems remain separate in the vector store, each with its own eval gate (`evals.yml`). A PR that drops an eval score below threshold does not merge.
5. **Terraform-only infra.** All infrastructure is Terraform under `terraform/envs/prod` (plus one-time `terraform/bootstrap`). No console-driven resource changes.
6. **Never invent metrics.** Cost and latency come from `scripts/benchmark.py` runs or Langfuse traces. Prices come from `config/prices.yaml`, verified against the AWS Price List.
7. **Untrusted retrieved text.** Treat retrieved context as untrusted (prompt injection). Keep the prompt-injection suite (`evals/metrics/custom.py`) and output guard (`LicenceComposer.apply_output_policy` / `output_guard` stage) in place.
8. **Miles merges.** Agents do not merge PRs or trigger workflow runs (`workflow_dispatch` / ingest / eval-live / benchmark / deploy) without his go-ahead.

---

## Engineering standards

- **Typed code.** Type hints on public functions and methods. Pydantic models at API boundaries.
- **Tests as the spec.** Prefer known-answer / golden cases. Cover happy path, edge cases, licence and injection behaviour where relevant.
- **Green before PR.** `ruff check` / `ruff format --check`, frontend `npm run typecheck` + `npm run build`, and the relevant pytest suite must pass locally. Existing CI must stay green.
- **Small, focused PRs.** One concern per PR; clear title and description; state assumptions and out-of-scope items.
- **No secrets in git.** Use Secrets Manager (prod) or local env / docker-compose (dev). Never commit keys or account IDs.
- **Pin versions for production-bound work.** Prefer pinned dependency and model versions when hardening; do not silently bump models in a feature PR.
- **Structured logging.** Prefer structured request metrics (`rag_request_metrics`) and stage timings. Do not log secrets, full prompts, or Class C full text.
- **AI outputs evaluated.** Changes that affect retrieval or generation must respect eval gates and thresholds in `evals/thresholds.yaml`.
- **Docs track behaviour.** Update README / ADRs / this file when behaviour, contracts, or run instructions change.

### Definition of done

- [ ] RAG rules above respected (licence guard, collections, secrets, metrics honesty)
- [ ] Types and Pydantic contracts in place at boundaries
- [ ] Tests added or updated; licence / injection coverage when those paths change
- [ ] Lint and tests pass (`make lint-python` / `pytest` / `web` typecheck+build, or CI equivalents)
- [ ] Eval gates still pass for affected collections (do not lower thresholds to green CI)
- [ ] No secrets introduced
- [ ] Docs updated if behaviour or workflow changed

---

## How to run, test, eval, and deploy

### Setup

```bash
pip install -e ".[dev]"
pre-commit install          # optional; see .pre-commit-config.yaml
docker compose up -d        # Postgres 16 + pgvector
export DATABASE_URL=postgresql://rag:raglocal@localhost:5432/ragplatform
python -m ingest.migrations.runner
python scripts/seed_ci_corpus.py
```

Frontend (optional, for UI work):

```bash
cd web && npm install && npm run dev
```

### Run API locally

```bash
uvicorn app.api.main:app --reload --port 8000
# health: /healthz  ready: /readyz
```

Ingest (needs AWS credentials + Bedrock for embeddings):

```bash
python -m ingest run --collection complex-systems --limit 3
```

### Test and lint

```bash
ruff check .
ruff format --check .
pytest -q tests/unit tests/integration tests/api tests/ingest

cd web && npm run typecheck && npm run build

make fmt-check              # terraform fmt -check
make lint-tf                # tflint (requires tflint installed)
```

### Eval

```bash
make eval COLLECTION=complex-systems FAST=1
# or: python3 evals/run.py --collection complex-systems --fast
# live golden set: make eval COLLECTION=complex-systems GOLDEN=golden_live.jsonl
```

Thresholds: `evals/thresholds.yaml` (per collection). Reports land in `evals/reports/`.

### Benchmark (measured cost / latency)

```bash
python scripts/benchmark.py --base-url https://rag.mileswaite.net
# or the Benchmark workflow (workflow_dispatch only)
```

Do not invent numbers for `docs/performance.md` — update from benchmark output or Langfuse.

### Deploy (humans / Miles)

1. Merge to `main` (Miles only).
2. **Terraform** workflow applies `terraform/envs/prod` on push to `main` when `terraform/**` changes (`environment: production`).
3. **Deploy Web** runs after a successful Terraform workflow on `main` (or `workflow_dispatch`): build ARM64 image → ECR → ECS force deploy.
4. **Ingest** / **Eval Live** / **Benchmark** are `workflow_dispatch` only — do not trigger without Miles's go-ahead.

---

## Existing CI (do not add or rename workflows)

Seven workflows already exist. **Do not** add lint, test, or eval workflows, and **do not** rename or edit these files unless Miles explicitly asks.

| Workflow | File | Triggers | Role |
|---|---|---|---|
| **Python** | `python.yml` | PR/push to `main` on `**/*.py`, `pyproject.toml`, `tests/**` | Ruff, pytest (`unit`/`integration`/`api`/`ingest`), `web` typecheck+build |
| **Evaluation Gates** | `evals.yml` | PR/push to `main` on `app/**`, `ingest/**`, `evals/**`, `collections/**`, `pyproject.toml` | **Required per-collection eval gates** (Complex Systems + UK Tax placeholder); injection covered inside CS gate when `AWS_EVAL_ROLE_ARN` is set |
| **Eval Live** | `eval-live.yml` | `workflow_dispatch` only | Production RDS eval via ECS Fargate |
| **Benchmark** | `benchmark.yml` | `workflow_dispatch` only | Live latency/cost via `scripts/benchmark.py` |
| **Deploy Web** | `deploy.yml` | Successful **Terraform** workflow on `main`, or `workflow_dispatch` | Build/push web image, ECS deploy |
| **Ingest** | `ingest.yml` | `workflow_dispatch` only | Build ingest image, run Fargate ingest task |
| **Terraform** | `terraform.yml` | PR/push to `main` on `terraform/**` | fmt, validate, tflint, plan (PR); apply on `main` |

**Path-trigger caution:** Do not add push/PR workflows (or edit files under `terraform/**`) that would unnecessarily fire `terraform.yml` → `deploy.yml`. Docs/config PRs should stay outside `terraform/**` and `.github/workflows/`.

Pre-commit (local): Terraform fmt, Ruff, yamllint, gitleaks, standard file hooks — see `.pre-commit-config.yaml`. Dependabot: `.github/dependabot.yml` (pip, npm, GitHub Actions only).

---

## Workflow for agents

1. **Read before writing.** Inspect the real layout, ADRs, neighbouring tests, and this file. Match existing patterns.
2. **Plan large changes.** For multi-file or cross-cutting work, outline approach, files touched, and risks before coding. Keep scope to the assigned task.
3. **Do not weaken tests or thresholds.** Never delete, skip, or loosen assertions / eval gates solely to make CI pass.
4. **State assumptions in the PR.** Call out env expectations, concurrent work, and follow-ups.
5. **Docs/config-only vs product code.** If the task says docs/config only, do not change application behaviour.
6. **Do not merge or dispatch workflows** without Miles's go-ahead.
7. **Cursor rules.** Follow `.cursor/rules/*.mdc`; they summarise this file for scoped globs. When in conflict, **this file wins**.

---

## Related docs

- [CONTRIBUTING.md](CONTRIBUTING.md) — short human setup and PR conventions
- [README.md](README.md) — product overview and quick start
- [docs/decisions/](docs/decisions/) — architecture decision records
- [docs/langfuse.md](docs/langfuse.md) — tracing setup (keys in Secrets Manager only)
- [docs/performance.md](docs/performance.md) — measured latency/cost (benchmark output)
- [docs/phase-2-deploy.md](docs/phase-2-deploy.md) — deploy order and HTTPS notes
