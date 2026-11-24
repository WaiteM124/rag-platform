# RAG Platform

Production-grade multi-collection RAG platform on AWS demonstrating end-to-end AI system operation: infrastructure as code, eval-gated CI/CD, licence-aware retrieval, tracing, and cost visibility.

**Author:** Miles Waite  
**Status:** Phase 2 (public demo UI + API)

### UI (Phase 2)

| Dark (default) | Light |
| --- | --- |
| ![Phase 2 home — dark](docs/screenshots/phase-2-dark.png) | ![Phase 2 home — light](docs/screenshots/phase-2-light.png) |

Tailwind + Radix primitives, self-hosted Inter, SSE chat with citations drawer, and strict CSP (no CDN).

## Architecture

```mermaid
flowchart TB
    subgraph "Client"
        UI[React SPA<br/>S3 + CloudFront]
    end

    subgraph "AWS eu-west-2"
        subgraph "Public Subnets"
            ALB[Application<br/>Load Balancer]
            subgraph "ECS Fargate"
                API[FastAPI Service<br/>0.5 vCPU / 1 GB]
            end
        end

        subgraph "Private Subnets"
            RDS[(PostgreSQL 16<br/>+ pgvector<br/>db.t4g.micro)]
        end

        subgraph "AWS Services"
            Bedrock[Amazon Bedrock<br/>Qwen3 235B / Titan V2]
            SM[Secrets Manager]
            ECR[ECR]
        end
    end

    subgraph "External"
        Langfuse[Langfuse Cloud EU<br/>Tracing]
        Fallback[Fallback LLM<br/>Provider]
    end

    UI -->|HTTPS| ALB
    ALB --> API
    API -->|Hybrid Retrieval| RDS
    API -->|Generate / Embed| Bedrock
    API -->|Fallback| Fallback
    API -->|Traces| Langfuse
    API -->|Secrets| SM

    classDef aws fill:#FF9900,color:#000
    classDef external fill:#4A90A4,color:#fff
    class ALB,API,RDS,Bedrock,SM,ECR aws
    class Langfuse,Fallback external
```

## Collections

The platform serves multiple document collections with a UI selector:

| Collection | Status | Sources | Description |
|------------|--------|---------|-------------|
| **Complex Systems** | Phase 1 | 46 verified | Academic papers, textbooks, lecture notes on complexity science |
| **UK Tax** | Phase 5 | 22 verified (draft) | GOV.UK guidance on VAT, MTD, IR35 |

Each collection has its own:
- Source registry with licence metadata
- Golden evaluation set (~100-120 questions)
- System prompts and configuration
- CI gate thresholds

## Bedrock models (eu-west-2)

| Role | Default model ID | Why |
|------|------------------|-----|
| **Answer / generation** | `qwen.qwen3-235b-a22b-2507-v1:0` | Open-weight Converse model while Claude account access is pending |
| **Eval judge (Ragas)** | `deepseek.v3.2` | Different model family from the answer model to reduce self-preference bias |
| **Embeddings** | `amazon.titan-embed-text-v2:0` | Unchanged 1024-d Titan V2 |

Override with `ANSWER_MODEL_ID` / `RAG_ANSWER_MODEL_ID` and `JUDGE_MODEL_ID` / `RAG_JUDGE_MODEL_ID`. IAM still allows the Anthropic EU inference profiles so switching back to **Claude Haiku** (`eu.anthropic.claude-haiku-5-5`) for A/B comparison is config-only. Qwen3 extended-thinking tags are stripped from streamed responses before they reach the UI.

Token costs for the spend ledger are loaded from `config/prices.yaml` (verify against [Bedrock pricing](https://aws.amazon.com/bedrock/pricing/) periodically).

## Licence-Aware Retrieval

All sources are classified by licence for legal compliance:

| Class | Licence Types | API Behaviour |
|-------|---------------|---------------|
| **A** | CC BY, CC0, OGL, MIT | Full text with attribution |
| **B** | CC BY-NC-SA | Full text while app is non-commercial; flagged |
| **C** | arXiv non-exclusive, All Rights Reserved | ≤300 char excerpt + link; never serve full chunks |

The response composer enforces these rules automatically:
- Class C text is used for retrieval/grounding but output is capped
- N-gram overlap detection prevents excessive quoting
- Every response includes proper attribution and source links
- A `commercial` flag in Terraform flips Class B → C behaviour if needed

## Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Compute** | ECS Fargate (ARM/Graviton) | No cold starts, SSE streaming, ~$17/mo vs ~$37+ with NAT for Lambda |
| **Database** | RDS PostgreSQL 16 + pgvector | ~$16/mo vs ~$400/mo OpenSearch Serverless floor |
| **LLM** | Amazon Bedrock (Qwen3 235B, Converse) | Open-weight answer model in eu-west-2; config switch to Claude |
| **Embeddings** | Titan Text Embeddings V2 | 1024-d, $0.0001/1K tokens |
| **Retrieval** | Hybrid (FTS + HNSW + RRF + reranker) | Exact token matching for maths/tax codes |
| **IaC** | Terraform | Remote state in S3, GitHub OIDC, no stored keys |
| **Tracing** | Langfuse Cloud EU | Free hobby tier, 50K units/mo |
| **CI/CD** | GitHub Actions | Eval gates per collection before deploy |

## Project Structure

```
rag-platform/
├── app/                      # FastAPI service
├── ingest/                   # Document ingestion pipeline
├── evals/                    # Golden sets, metrics, gates
├── collections/              # Per-collection config and sources
│   ├── complex-systems/
│   └── uk-tax/
├── terraform/
│   ├── bootstrap/            # One-time setup (CloudShell)
│   ├── envs/prod/            # Production environment
│   └── modules/              # Reusable modules
├── docs/                     # Build plan, source lists, ADRs
└── .github/workflows/        # CI/CD pipelines
```

## Roadmap

### Phase 0: Foundations ✅
- [x] Repo scaffold and documentation
- [x] Terraform bootstrap (S3 state, OIDC, IAM roles, Budget)
- [x] VPC skeleton (no NAT)
- [x] GitHub Actions CI/CD
- [x] Pre-commit hooks

### Phase 1: Complex Systems RAG core (current)
- [x] Source registry (`collections/complex-systems/sources.yaml`, 46 sources)
- [x] Ingest fetchers (arXiv `/src`, PDF, HTML/PLOS/PMC/LibreTexts)
- [x] Licence validation (ingest fails without licence metadata)
- [x] Chunking, Titan V2 embeddings, pgvector + FTS schema
- [x] Hybrid retrieval + Bedrock Converse answers + licence composer
- [x] Eval harness v1 (golden set, injection, thresholds)
- [x] Terraform: RDS + ECS ingest task + ECR (prod)

### Phase 2: Retrieval + API + v1 Live
- [x] Hybrid retrieval with RRF
- [x] FastAPI service with SSE
- [x] Response composer with licence enforcement
- [x] Portfolio UI with collection cards + streaming chat
- [ ] Deploy to production (`rag.mileswaite.net`; see [docs/phase-2-deploy.md](docs/phase-2-deploy.md))

### Phase 3: Evals and CI Gates
- [ ] Complex Systems golden set (~120 questions)
- [ ] Eval harness with LLM judge
- [ ] CI gates blocking failed releases
- [ ] Public /evals and /costs pages

### Phase 4: Hardening
- [ ] Threat model controls
- [ ] Autoscaling and alarms
- [ ] Load testing

### Phase 5: UK Tax Collection
- [ ] Complete source list (25-40)
- [ ] GOV.UK-specific ingester
- [ ] UK Tax golden set and gates

### Next phases (after Phase 1)
- **Phase 2:** FastAPI on Fargate, ALB, domain, SSE `/query`, minimal UI
- **Phase 3:** Langfuse tracing, public `/evals` and `/costs`, full Ragas CI with reranker eval
- **Phase 4:** Autoscaling, threat-model hardening, scheduled re-ingest
- **Phase 5:** UK Tax collection

### Phase 6: Public Launch
- [ ] Demo video and write-up
- [ ] Security review
- [ ] Privacy notice

## Performance

Measured p50/p95 latency and per-query token cost live at
[docs/performance.md](docs/performance.md) (template until the **Benchmark**
workflow or `scripts/benchmark.py` is run against the live site). Each answer
in the UI also shows a compact `took X ms, ~$Y` line from server-side `metrics`.

## Estimated Monthly Cost (v1 prod)

| Service | Estimate |
|---------|----------|
| ECS Fargate (0.5 vCPU, 1 GB ARM) | $17 |
| Application Load Balancer | $25 |
| Public IPv4 addresses | $11 |
| RDS db.t4g.micro + 20 GB | $16 |
| Secrets Manager (4 secrets) | $2 |
| Bedrock (3,000 queries/mo) | $2 |
| **Total** | **~$70-80/mo** |

## Getting Started

### Prerequisites

- AWS account with appropriate permissions
- Terraform >= 1.10.0 (required for S3 lockfile support)
- GitHub repository with Actions enabled

### Bootstrap (One-Time)

Run in AWS CloudShell with administrator access. CloudShell's bundled Terraform may be outdated, so install the required version first:

```bash
# Install Terraform 1.17.2 into ~/bin
mkdir -p ~/bin
curl -fsSL https://releases.hashicorp.com/terraform/1.17.2/terraform_1.17.2_linux_amd64.zip -o /tmp/terraform.zip
unzip -o /tmp/terraform.zip -d ~/bin
rm /tmp/terraform.zip
export PATH="$HOME/bin:$PATH"
terraform version  # Should show: Terraform v1.17.2

# Clone and apply bootstrap
git clone https://github.com/WaiteM124/rag-platform.git
cd rag-platform/terraform/bootstrap
terraform init
terraform plan -var="alert_email=your-email@example.com"
terraform apply -var="alert_email=your-email@example.com"
terraform output
```

### Configure GitHub (Required)

#### 1. Create the `production` Environment

The apply role trusts only the `production` GitHub environment:

1. Go to: **GitHub repo → Settings → Environments → New environment**
2. Name: `production`
3. Configure protection rules:
   - **Deployment branches**: Select "Selected branches" → Add `main`
   - **Required reviewers** (optional): Add reviewers for manual approval
4. Click **Save protection rules**

#### 2. Set Repository Variables

Go to: **GitHub repo → Settings → Secrets and variables → Actions → Variables**

| Variable | Value |
|----------|-------|
| `AWS_REGION` | `eu-west-2` |
| `TF_STATE_BUCKET` | `terraform output state_bucket_name` |
| `AWS_PLAN_ROLE_ARN` | `terraform output plan_role_arn` |
| `AWS_APPLY_ROLE_ARN` | `terraform output apply_role_arn` |
| `AWS_EVAL_ROLE_ARN` | `terraform output eval_role_arn` (after bootstrap re-apply) |

### Bootstrap re-apply (required for Phase 1)

After pulling Phase 1, re-run bootstrap from **AWS CloudShell** (admin) to create the `rag-platform-eval` OIDC role and extended apply permissions:

```bash
cd rag-platform/terraform/bootstrap
terraform apply -var="alert_email=your-email@example.com"
terraform output eval_role_arn
```

Set GitHub variable `AWS_EVAL_ROLE_ARN` to that ARN.

### Local development

```bash
pip install -e ".[dev]"
docker compose up -d
export DATABASE_URL=postgresql://rag:raglocal@localhost:5432/ragplatform
python -m ingest.migrations.runner  # or: python -c "from ingest.migrations.runner import run_migrations; run_migrations('$DATABASE_URL')"
python scripts/seed_ci_corpus.py     # small fixture corpus
pytest -q

# Ingest (needs AWS credentials + Bedrock for embeddings)
python -m ingest run --collection complex-systems --limit 3

make eval COLLECTION=complex-systems FAST=1
```

**Cost notes (prod, Phase 1 lean footprint):** RDS `db.t4g.micro` + 20 GB gp3 ≈ **$16/month**; ECS ingest runs are on-demand Fargate only when triggered; no ALB/NAT in Phase 1.

See `docs/phase-1-architecture.md` for the Phase 1 diagram and Bedrock model defaults.

## Security

- **No secrets in repo**: All credentials in AWS Secrets Manager
- **OIDC authentication**: No long-lived AWS keys in GitHub
- **Immutable ID pinning**: Trust policies pin GitHub's immutable owner/repo numeric IDs in the OIDC `sub` claim (e.g., `@351398746`, `@1468576170`), preventing repo-name reuse attacks
- **Least-privilege CI roles**:
  - Plan role trusts only `pull_request` events
  - Apply role trusts only `environment:production` (requires GitHub environment)
  - IAM writes scoped to `rag-platform-*` resources only
  - Self-modification explicitly denied (roles cannot modify themselves)
  - `iam:PassRole` restricted to ECS tasks only
- **Licence compliance**: Automated enforcement of source licences
- **Input validation**: Rate limits, size caps, spend caps
- **Tracing**: Full observability via Langfuse

See `docs/build-plan.md` §7 for the full threat model.

## Licence

MIT License - see [LICENSE](LICENSE)

Copyright (c) 2026 Miles Waite
