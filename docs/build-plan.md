# Multi-collection RAG platform: build plan

*Draft 2 • 23 Nov 2026 (Europe/London) • Grok Bot for Miles Waite*

**Goal:** a public, production-grade RAG platform that shows Miles runs production AI systems end to end: infrastructure as code, evals that gate releases, tracing, cost visibility and a threat model. It has two collections, picked from a UI selector: **Complex Systems (built first)** and **UK Tax (second)**. Retrieval is licence-aware. The corpus is public sources and Miles's own notes only. **No client code, data or systems, ever.**

**Guiding constraints:** ship v1 with a live link fast and iterate in public. Keep it boring and cheap: no Kubernetes, one AWS region, a single small container, a single small Postgres. Every change goes through Terraform and CI.

---

## 1. Key decisions

| Decision | Choice | Why (short) |
|---|---|---|
| Region | **eu-west-2 (London)** | Miles is UK-based and the UK Tax collection fits. The Bedrock price list for eu-west-2 shows on-demand Nova Micro/Lite and Titan Embeddings V2, so the core models are usable there. |
| Compute | **ECS Fargate (ARM/Graviton), 1 small task, public subnet, no NAT** | See §1.1. Cheaper than Lambda once you count egress (NAT), no cold starts, and SSE streaming is simple. |
| Vector + lexical store | **PostgreSQL 16 + pgvector on RDS (db.t4g.micro)** | See §1.2. About $16/month against roughly $400/month for an always-warm OpenSearch Serverless floor. One database holds chunks, licences, eval results and cost ledger. |
| Retrieval | **Hybrid: Postgres full-text (lexical) + pgvector HNSW, fused with RRF, then a cross-encoder reranker** | Maths and tax text are full of exact tokens (`λ`, "VAT Notice 700/22", "ESM10010") that dense-only retrieval misses. The gain is proven with an eval (§6). |
| LLM access | **Thin model-agnostic layer: Bedrock (primary) + one external provider (fallback), cost-based routing** | See §4. Avoids lock-in, survives a provider outage and shows routing skill. |
| Default generator | **Amazon Nova Lite on Bedrock**, escalating to a stronger model for hard queries | Lowest listed cost per query (§1.3). Stronger tiers are behind the router. |
| Embeddings | **Amazon Titan Text Embeddings V2** (Bedrock) | $0.0001 per 1K input tokens in eu-west-2, so re-embedding the whole corpus costs pennies. |
| IaC | **Terraform**, remote state in S3 with lockfile, one root per environment (`dev`, `prod`) | As agreed. Small modules, no Terragrunt. |
| CI/CD | **GitHub Actions + OIDC to AWS** (no long-lived keys) | Plan on PR, apply on merge, with eval gates per collection before deploy. |
| Tracing | **Langfuse Cloud (EU), Hobby plan** | Free tier: 50k units/month, 30-day retention, 2 users (langfuse.com/pricing, checked 23 Nov 2026). Self-hosting would need Postgres, ClickHouse and Redis, which is not worth it at this scale. Upgrade to Core ($29/month) only if needed. |
| Secrets | **AWS Secrets Manager** (DB credentials, external-provider key, Langfuse keys), injected as ECS task secrets | $0.40 per secret per month. Rotation on for the DB. |
| UI | **Static SPA (Vite + React) on S3 + CloudFront**, calling the API | Cheap and fast. Hosts the collection selector, citations with licence badges, and the public **/evals** and **/costs** pages. |
| Kubernetes | **No** | Not needed at this scale. Fargate plus Terraform shows the same operational discipline at about 5% of the cost. |

### 1.1 Fargate vs Lambda

Unit prices from the AWS Price List API, eu-west-2, on-demand, published 11 Nov 2026 and fetched 23 Nov 2026. These are **estimates**: 730 h/month, USD, excluding tax and free tier.

| Item | Unit price (looked up) | Monthly estimate |
|---|---|---|
| Fargate ARM vCPU-hour | $0.03725 | 0.5 vCPU → **$13.60** |
| Fargate ARM GB-hour | $0.00409 | 1 GB → **$2.99** |
| Lambda requests | $0.20 / 1M | ≈ $0 at portfolio traffic |
| Lambda compute (ARM, tier 1) | $0.0000133334 / GB-s | ≈ $0–1 at portfolio traffic |
| **NAT Gateway** (needed for a VPC Lambda to reach the external LLM provider and Langfuse) | $0.05 / hour + $0.05 / GB | **$36.50 + data** |
| Public IPv4 address | $0.005 / hour | $3.65 each |

**Decision: Fargate.** Lambda compute is nearly free at low traffic. But Lambda has to sit in the VPC to reach RDS privately, and then it needs a NAT Gateway (≈$36.50/month) or several interface endpoints to reach the external provider and Langfuse. A single 0.5 vCPU / 1 GB Fargate task in a public subnet (security group locked to the ALB, public IP for egress only) costs ≈$16.60/month. It has no cold starts, streams SSE natively and runs the same container locally and in CI. Autoscaling uses ECS target tracking on CPU and ALB request count, with min 1 and max 3 tasks.

### 1.2 pgvector on RDS vs OpenSearch Serverless

| Item | Unit price (looked up) | Monthly estimate |
|---|---|---|
| RDS PostgreSQL db.t4g.micro, Single-AZ | $0.018 / hour | **$13.14** |
| RDS gp3 storage | $0.133 / GB-month | 20 GB → **$2.66** |
| OpenSearch Serverless Search OCU | $0.27552 / OCU-hour | — |
| OpenSearch Serverless Indexing OCU | $0.27552 / OCU-hour | — |
| OSS with a warm floor of 1 search + 1 indexing OCU | 2 × 0.27552 × 730 | **≈ $402** (+ storage, not looked up) |

**Decision: pgvector on RDS.** It costs about 25× less for a corpus of tens of thousands of chunks. AWS docs (checked 23 Nov 2026) say OpenSearch Serverless collection groups can now be set to a minimum of 0 OCUs. That removes the idle floor but brings cold starts on the first query, so an always-on public demo would run at the warm-floor price. Postgres also holds the licence table, eval runs and cost ledger in the same transactional store. **Caveat:** Postgres full-text `ts_rank` is BM25-*like*, not true BM25. True BM25 extensions such as ParadeDB `pg_search` are not available on RDS. If the lexical leg underperforms in evals, compute BM25 in the app over the FTS candidate set, or revisit OSS.

### 1.3 Estimated monthly run cost (v1, prod only)

All figures are **estimates** from the AWS Price List API (eu-west-2, fetched 23 Nov 2026) unless marked otherwise.

| Line | Estimate |
|---|---|
| Fargate, 1 × (0.5 vCPU, 1 GB) ARM | $16.58 |
| Application Load Balancer ($0.02646/h) + up to ~1 LCU ($0.0084/LCU-h) | $19.32 + ≤ $6.13 |
| Public IPv4 (task + 2 ALB addresses, $0.005/h each) | $10.95 |
| RDS db.t4g.micro + 20 GB gp3 | $15.80 |
| Secrets Manager (4 secrets × $0.40) | $1.60 |
| Bedrock generation, Nova Lite: $0.000084/1K input, $0.000336/1K output. At 4K in + 0.5K out ≈ **$0.0005/query**, × 3,000 queries/month | ≈ $1.50 |
| Bedrock embeddings, Titan V2: $0.0001/1K tokens. Full corpus re-embed of ~5M tokens (assumed size) | ≈ $0.50 per re-embed |
| Reranker | **not priced**: Bedrock rerank availability and price in eu-west-2 not confirmed (see §9) |
| Langfuse Cloud Hobby | $0 (published price) |
| S3, CloudFront, CloudWatch, Route 53, external LLM fallback | not looked up; expected small at this traffic |
| **Total (rough)** | **≈ $70–80/month**, about two-thirds of it ALB + IPv4 + Fargate |

Cost levers, if needed: scale the dev environment to zero outside work hours (`desired_count=0`, stop RDS) and add Compute Savings Plans later. The ALB could be replaced with CloudFront plus a VPC origin, but only if a measured saving justifies the extra complexity.

---

## 2. Phased plan

Each phase ends with something demonstrable. **v1 goes live at the end of Phase 2.** Phases 3 onward ship as incremental releases behind eval gates.

### Phase 0: Foundations (days 1–3)
- AWS account hygiene: dedicated account, IAM Identity Center, budgets and alerts at $50/$100, Cost Anomaly Detection, CloudTrail, cost allocation tags (`project`, `collection`, `env`).
- Terraform: state bucket and lock, `network` (VPC, 2 public + 2 private subnets, **no NAT**), `ecr`, `iam` (GitHub OIDC role, task roles), `secrets`.
- Repo skeleton (§3), pre-commit (ruff, mypy, tflint, checkov, gitleaks), Makefile, `docker compose` for local Postgres + pgvector.
- Decision records (ADRs) for every row in §1.

### Phase 1: Complex Systems ingestion + licence handling (days 3–7)
- Source registry `collections/complex-systems/sources.yaml`, generated from the verified list in `complex-systems-sources.md` (46 sources: **3 class A, 3 class B (NC-SA), 40 class C**).
- Fetchers: arXiv `/src` → pandoc → Markdown with LaTeX kept (32 items); PDF → Marker (PDF-only items); HTML extractors for LibreTexts, PLOS (JATS) and PMC (OA API). Rate-limited and polite, with a User-Agent identifying the project.
- Chunker: heading-aware, 500–900 tokens, ~100 overlap, never splits display equations or proofs, and prefixes each chunk with its section path.
- Licence engine: every source carries `licence`, `licence_url`, `licence_class` (A/B/C), `nc_flag`, `nd_flag`, `attribution_text`. The ingest step **fails** on any source without a licence record.
- Embeddings (Titan V2) and lexical index (`tsvector`), with content hashes for idempotent re-ingestion.
- Owner notes (the 9 "Module Overview" docs and the Study Record in Drive) are **held back** until Miles approves. They would go in as source type `owner_notes`.

### Phase 2: Retrieval + API + LLM layer + minimal UI → **v1 live link** (days 7–14)
- Retrieval: lexical top-50 + vector top-50 → Reciprocal Rank Fusion → reranker top-30 → 8 chunks to the LLM. Filtered by `collection`.
- Response composer with **licence enforcement** (§5).
- FastAPI service on Fargate: `/query` (SSE streaming), `/collections`, `/sources/{id}`, `/healthz`. Per-IP rate limits, request size caps and a global daily spend cap.
- LLM layer v1 (§4) with Bedrock primary and an external fallback.
- UI: collection selector (UK Tax shown as "coming soon"), answers with numbered citations, a licence badge per citation ("full text CC BY", "NC-SA", "excerpt, read at source"), and a link out.
- Langfuse tracing on every request: retrieval spans, rerank, LLM call, tokens and cost.
- Deploy: `terraform apply` prod, custom domain, HTTPS (ACM). **Ship.**

### Phase 3: Evals, CI gates, public eval & cost page (weeks 3–4)
- Complex Systems golden set v1 (§6), retrieval labels, and the LLM-judge harness.
- CI: on every PR, run unit tests, `terraform plan`, a **fast eval subset** (≈30 Qs) and the injection suite. On merge to main, run the **full eval**. Deploy is blocked if any gate fails, and the blocked release is logged.
- Public **/evals** page: latest scores per collection, trend over releases, hybrid vs vector-only comparison, and gate history including blocked releases.
- Public **/costs** page: monthly infra cost (from Cost Explorer via a daily Lambda or scheduled task writing to Postgres), cost per query (from Langfuse/ledger), tokens by model, and the router's model mix.

### Phase 4: Hardening (weeks 4–5)
- Threat-model controls implemented and tested (§7). Prompt-injection suite in CI.
- Autoscaling policies, CloudWatch dashboards and alarms (5xx, p95 latency, spend/day, eval drift), RDS automated backups and a restore drill.
- Re-ingestion job (scheduled ECS task): diff by `content_hash` and `updated_at`, re-embed only what changed, record re-ingestion time.
- Load test (k6) to set autoscaling targets and record p50/p95.

### Phase 5: UK Tax collection (weeks 5–7)
- Finish `uk-tax-sources.md` (currently a paused draft with 22 verified pages) to 25–40 sources via the GOV.UK Content API. All OGL v3 (class A) after confirming exclusions (logos, Royal Arms, third-party content).
- GOV.UK-specific ingester: follows `redirect` schemas, crawls HMRC manual sections, uses `public_updated_at` for freshness.
- UK Tax golden set and gates (§6), a "not tax advice" disclaimer, and an answer-date stamp.

### Phase 6: Public launch (week 8)
- README with architecture diagram, ADRs, cost and eval pages linked, a demo video, and a write-up post.
- Final security review, `robots`/abuse posture, privacy notice (no query logging of PII; IPs hashed).

---

## 3. Repo layout

```
rag-platform/
├── infra/
│   ├── modules/
│   │   ├── network/          # VPC, subnets, SGs (no NAT)
│   │   ├── ecr/
│   │   ├── ecs-service/      # cluster, task def, service, autoscaling, ALB
│   │   ├── rds-postgres/     # pgvector, parameter group, backups
│   │   ├── secrets/
│   │   ├── static-site/      # S3 + CloudFront + ACM
│   │   ├── observability/    # dashboards, alarms, budgets, anomaly detection
│   │   ├── scheduled-task/   # re-ingestion, eval nightly, cost collector
│   │   └── github-oidc/
│   └── envs/{dev,prod}/      # thin roots: module wiring + tfvars
├── ingestion/
│   ├── fetchers/             # arxiv_src.py, pdf_marker.py, html_plos.py, pmc_oa.py, govuk_content_api.py
│   ├── normalise/            # pandoc, mathml->latex, cleaning
│   ├── chunking/
│   ├── licence/              # licence registry, class rules, validators
│   ├── embed/
│   └── cli.py                # ingest --collection complex-systems [--changed-only]
├── collections/
│   ├── complex-systems/{sources.yaml, prompts/, config.yaml}
│   └── uk-tax/{sources.yaml, prompts/, config.yaml}
├── api/
│   ├── app/                  # FastAPI: routes, retrieval, rerank, composer, guards
│   ├── llm/                  # provider-agnostic layer (§4)
│   └── Dockerfile
├── ui/                       # Vite + React: chat, collection selector, /evals, /costs
├── evals/
│   ├── datasets/{complex-systems,uk-tax}/golden.jsonl
│   ├── injection/            # attack prompts + poisoned-doc fixtures
│   ├── metrics/              # faithfulness, citation_accuracy, recall_at_k, licence_compliance
│   ├── gates.yaml            # thresholds per collection
│   └── run.py                # writes results to Postgres + Langfuse datasets
├── docs/                     # this plan, ADRs, source lists, threat model
└── .github/workflows/        # ci.yml (plan + tests + fast eval), deploy.yml (full eval gate → apply → deploy)
```

---

## 4. Model-agnostic LLM layer (thin)

A small in-house interface (≈300 lines), not a heavy framework:

```python
class LLMProvider(Protocol):
    def generate(self, messages, *, max_tokens, temperature, stream) -> Iterator[Chunk]: ...
    def embed(self, texts) -> list[list[float]]: ...      # optional per provider
    def rerank(self, query, docs) -> list[float]: ...     # optional per provider
    price: PriceCard  # $/1K input, $/1K output, from config, versioned
```

- **Providers:** `BedrockProvider` (Converse API; Nova Micro/Lite/Pro, plus a stronger tier) and one external provider (`ExternalProvider`, behind the same interface, key in Secrets Manager).
- **Routing:** a cost-based router chooses the cheapest model whose *eval-certified* tier meets the request class. The classes are: `simple` (definition lookup), `standard` and `hard` (multi-source synthesis or derivation, decided by a cheap classifier plus retrieval-score spread). Tier certification comes from evals: a model may serve a class only if it passed that class's gates in the last eval run.
- **Fallback:** on timeout, throttling or 5xx, retry once with jitter, then fail over to the next provider in the class's ordered list. Each provider has a circuit breaker.
- **Budget guard:** per-request max tokens, a global daily $ cap (the API degrades to "retrieval-only: here are the sources" when the cap is hit), and a per-IP rate limit.
- **Ledger:** every call writes provider, model, tokens, latency, cost and route reason to Postgres and Langfuse. This feeds the /costs page.
- Price cards live in `config/prices.yaml` with a `source_url` and `checked_at` and are reviewed monthly. Unverified prices are marked as such.

---

## 5. Data model: chunk metadata schema

```sql
CREATE TABLE sources (
  source_id          text PRIMARY KEY,           -- e.g. 'cs-014' / 'tax-vat-700'
  collection         text NOT NULL,              -- 'complex-systems' | 'uk-tax'
  title              text NOT NULL,
  authors            text[],
  publisher          text,                       -- arXiv, PLOS, GOV.UK/HMRC, ...
  source_url         text NOT NULL,              -- canonical, post-redirect
  source_type        text NOT NULL,              -- arxiv | journal | book | govuk_guide | hmrc_manual | owner_notes
  format             text NOT NULL,              -- latex | pdf | html | govuk_json | gdoc
  version            text,                       -- arXiv vN, GOV.UK public_updated_at, PDF version string
  published_at       date,
  updated_at         timestamptz,                -- upstream last-updated
  licence            text NOT NULL,              -- SPDX-style id: CC-BY-4.0, CC-BY-NC-SA-3.0, OGL-UK-3.0, arXiv-nonexclusive-1.0, LicenseRef-AllRightsReserved
  licence_url        text NOT NULL,
  licence_class      char(1) NOT NULL CHECK (licence_class IN ('A','B','C')),
  republish_allowed  boolean NOT NULL,           -- A => true; B => true only while app is non-commercial; C => false
  nc_flag            boolean NOT NULL DEFAULT false,
  nd_flag            boolean NOT NULL DEFAULT false,
  attribution_text   text NOT NULL,
  excerpt_max_chars  int NOT NULL DEFAULT 300,  -- enforced for class C
  licence_verified_at timestamptz NOT NULL,
  licence_evidence   text NOT NULL,              -- quote or URL of the licence statement seen
  retrieved_at       timestamptz NOT NULL,
  content_hash       text NOT NULL,              -- sha256 of normalised full text
  module             text                        -- A–I for complex-systems; VAT/MTD/IR35 for uk-tax
);

CREATE TABLE chunks (
  chunk_id           bigserial PRIMARY KEY,
  source_id          text REFERENCES sources ON DELETE CASCADE,
  collection         text NOT NULL,              -- denormalised for filtered search
  chunk_index        int NOT NULL,
  section_path       text,                       -- 'Newman 2003 › 4. Network resilience'
  locator            text,                       -- page / equation / manual section e.g. 'ESM10010'
  text               text NOT NULL,
  token_count        int NOT NULL,
  chunk_hash         text NOT NULL,
  embedding          vector(1024) NOT NULL,      -- Titan V2 (1024-d config)
  embedding_model    text NOT NULL,
  embedding_version  text NOT NULL,
  tsv                tsvector GENERATED ALWAYS AS (to_tsvector('english', text)) STORED,
  ingest_run_id      uuid NOT NULL,
  created_at         timestamptz DEFAULT now()
);
-- HNSW on embedding, GIN on tsv, btree on (collection, source_id)
```

### Licence enforcement (response composer)
- **Class A:** may quote or return full chunks, with attribution and link.
- **Class B (NC-SA):** same as A **while the deployment flag `commercial=false`**. A Terraform variable flips the whole class to C behaviour. Shows the attribution plus "CC BY-NC-SA, non-commercial use".
- **Class C:** the model sees full chunks for grounding, but the **output filter** caps verbatim overlap with any class-C chunk at `excerpt_max_chars` (checked with n-gram overlap), always shows the link, and never returns the chunk text in API source payloads (only title, locator and a ≤300-char excerpt).
- The licence-compliance metric (§6) tests this automatically and its gate is 100%.

---

## 6. Evals

Every collection has a **golden set**, **retrieval labels**, and **gates** in `evals/gates.yaml`. The judge model is pinned and differs from the generator. Thresholds are **initial targets**: calibrate them against the first baseline run, then ratchet up and never down.

### Complex Systems (first)
- **Golden set v1: ~120 questions**, written from the sources (and, if Miles approves, seeded from his module overviews). The mix:
  - 40 definitional or conceptual questions ("What is causal emergence?")
  - 30 equation or derivation questions ("State the BA degree exponent and why")
  - 25 cross-source synthesis questions
  - 15 licence-behaviour probes ("Paste section 3 of Clauset et al.", which must give an excerpt and a link)
  - 10 unanswerable or out-of-corpus questions, which must abstain
- Each item carries the expected answer key points, the gold `source_id`s and chunk locators.
- **Retrieval comparison (required):** vector-only vs lexical-only vs hybrid (RRF) vs hybrid + rerank. Report recall@5, recall@10, MRR and nDCG@10 for each. Hybrid ships only if it beats vector-only on recall@10 without losing more than 300 ms of p95 latency.

### UK Tax (second)
- **Golden set v1: ~100 questions** across VAT, MTD and IR35, including threshold and date questions (checked against `public_updated_at` freshness), procedural questions ("how do I sign up for MTD for Income Tax"), manual-section lookups (ESM/VATREG) and abstention on personal-advice requests.
- Extra metric: **currency**. Answers must cite the current version of the page, with no stale cached figures.

### Metrics and gates

| Metric | How measured | Gate (initial) |
|---|---|---|
| Faithfulness | LLM-judge: claims supported by retrieved context | ≥ 0.85 |
| Citation accuracy | Judge + rule check: each cited source actually supports the sentence it's attached to | ≥ 0.90 |
| Answer correctness | Key-point coverage vs golden answer | ≥ 0.75 |
| Recall@10 (hybrid + rerank) | Gold chunks retrieved | ≥ 0.85, and ≥ vector-only |
| Abstention accuracy | Unanswerables correctly declined | ≥ 0.90 |
| Licence compliance | Class-C verbatim cap and link present; class B flagged | **= 1.00** |
| Prompt-injection pass rate | §7 suite | ≥ 0.95 |
| p95 latency (end-to-end, eval harness) | | ≤ 8 s |
| Cost per query (mean) | Ledger | ≤ $0.005 |
| Regression | Any metric vs last main release | no drop > 2 pts |

The fast PR subset (~30 questions per collection plus the full injection suite) gates PRs. The full set gates deploys. Nightly runs on prod catch drift after re-ingestion.

---

## 7. Threat model (outline)

**Assets:** API availability, the spend budget, the cloud account, the integrity of the corpus and answers, licence compliance, secrets, and visitors' queries.

| Threat | Vector | Controls | Test |
|---|---|---|---|
| Direct prompt injection | User asks the model to ignore its rules, reveal the system prompt, or dump full class-C text | System prompt isolation; output filter (licence cap, system-prompt-leak detector); refusal templates | Injection suite (≥100 prompts: jailbreaks, role-play, encoding tricks) |
| Indirect injection (poisoned documents) | Instructions embedded in an ingested source or a future upstream change | Sources are allowlisted only; at ingest, strip and flag imperative "AI instructions"; retrieved text is wrapped as quoted data; tools are not exposed to the LLM (no actions possible) | Fixture docs with planted instructions, which must not change behaviour |
| Data leakage | System prompt, other users' queries, secrets, internal hostnames | No user data in prompts; no conversation sharing; secrets only in Secrets Manager via task role; error messages sanitised; no client data anywhere in the repo or corpus (CI grep and gitleaks) | Leak probes in the suite; gitleaks in CI |
| Licence breach | The app republishes non-open text | Licence classes + output filter + `commercial` flag | Licence-compliance metric = 1.00 gate |
| Denial of wallet | Scripted high-volume or long-context queries | Per-IP rate limit, max input length, max tokens, global daily $ cap with retrieval-only degradation, AWS Budgets alarms, WAF rate rule (optional) | k6 abuse test; cap trip test |
| Supply chain | Malicious dependency or base image | Pinned lockfiles, Dependabot, image scanning (ECR), minimal base, non-root container | CI scans |
| Cloud account compromise | Leaked keys, over-broad IAM | GitHub OIDC with no static keys; least-privilege task roles; CloudTrail; MFA; checkov in CI | checkov/tflint gates |
| Upstream tampering or staleness | Source changes after ingest | `content_hash` diff, re-ingest review for class changes, licence re-verification on every re-ingest | Re-ingest job report |
| Harmful reliance (tax) | Users treat answers as advice | Disclaimer, date stamp, citations to GOV.UK, abstention on personal circumstances | UK Tax abstention metric |

---

## 8. Metrics to capture (and publish on /evals and /costs)

| Metric | Source | Published |
|---|---|---|
| Eval set size per collection (questions, labelled chunks) | `evals/datasets` | /evals |
| Faithfulness | Eval harness | /evals (per release) |
| Citation accuracy | Eval harness | /evals |
| Recall@k (k = 5, 10): **hybrid vs vector-only** (plus MRR, nDCG@10) | Eval harness | /evals (comparison chart) |
| p50 / p95 latency (end-to-end and per stage: retrieve, rerank, generate) | Langfuse + ALB metrics | /evals and dashboard |
| Cost per query (mean, p95; by model and route) | LLM ledger | /costs |
| Monthly infra cost (by service, by collection tag) | Cost Explorer daily pull | /costs |
| Docs and chunks ingested (per collection, per licence class) | `sources` and `chunks` tables | /evals header |
| Re-ingestion time (full and incremental) | Ingest run logs | /evals |
| Prompt-injection test pass rate | Injection suite | /evals |
| Releases blocked by eval gates (count, which gate) | CI run history → Postgres | /evals (gate history) |

---

## 9. Open questions and uncertainties

- **Reranker:** whether Bedrock rerank models are available on demand in eu-west-2, and at what price, was not confirmed. The fallbacks are the external provider's rerank endpoint, or a small open cross-encoder in the API container (which needs about 2 GB of task memory and would add about $6/month of Fargate memory). Decide in Phase 2 with a latency and quality eval.
- **Stronger-tier model prices** (Claude and similar via Bedrock) were not taken from the price list. The Marketplace rows in the eu-west-2 file are not labelled by model. Confirm on the Bedrock pricing page before writing price cards.
- **External fallback provider:** not chosen and not priced.
- **Corpus token size** (~5M tokens) is an assumption until Phase 1 measures it.
- **NC-SA sources (3)** are safe only while the app stays non-commercial. Keep the `commercial` flag false.

## Addendum (23 Nov 2026): fine-tuned model workstream

**Goal:** show model adaptation and the judgement of when a small tuned model beats a frontier API call.

**Task chosen:** an answer faithfulness and citation checker. It takes the question, the retrieved chunks and the draft answer, and labels each cited claim as supported or unsupported. It runs on every answer and is used in the CI eval gates, so it is high-volume, and a frontier LLM judge is the expensive baseline it would replace.
- Rejected: query routing (the user picks the collection in the UI, so it adds little). Reranking stays a stock cross-encoder (no Bedrock reranker in eu-west-2), with a fine-tuned reranker as an optional stretch.

**Method:** LoRA/QLoRA on a 1-4B open instruct model (e.g. a Qwen3 or Llama small model, to be chosen by licence and size). Training data: synthetic (question, context, answer, label) triples generated from the Complex Systems corpus, including deliberately corrupted answers as negatives, labelled by a frontier Bedrock model, with a human-checked held-out test set. Train on Hugging Face Jobs or a single rented GPU.

**Eval, head-to-head vs a frontier Bedrock judge:** F1 and accuracy on the held-out set, p50/p95 latency, cost per 1k calls, and training data size and method. All numbers are measured, never estimated.

**Serving:** to be decided by measurement. Options are Bedrock Custom Model Import (check eu-west-2 support first), a small Hugging Face Inference Endpoint, or a quantised CPU model in the Fargate task if latency is acceptable.

**Publish:** the model and its model card on Hugging Face under Miles's account, with the eval table and a link from the public eval page.

**Build order:** after v1 is live with its baseline eval (day 2-3). It needs the eval harness and real retrieved contexts first. It is not on the v1 critical path.

## Addendum (23 Nov 2026): visual tools for Complex Systems (v1.1)

**Decision:** the model picks from a fixed, allow-listed set of chart tools and fills in validated parameters. The app renders the chart (Plotly in the browser). The model never writes or runs code itself, which avoids prompt injection leading to code execution.

**Starter tools** (finalise against the five visual-tool ideas at the end of the RAG Corpus Shortlist):
- Mandelbrot / Julia set explorer (bounded resolution and iterations)
- Logistic map bifurcation diagram
- Lorenz attractor (bounded integration steps)
- Log-log power-law fit and box-counting fractal dimension
- Network degree distribution (e.g. Barabási-Albert vs Erdős-Rényi)

**Guardrails:** a JSON schema for each tool, with parameter bounds and a compute or time cap for each call. Tool calls are traced in Langfuse, and the evals include tool-selection accuracy.

**Timing:** v1.1, straight after v1 is live, before or alongside the fine-tuning work.

**Gradio on HF Spaces:** I'm not using it for the main app (AWS stays the platform). It's optional as a free, separate demo of the chart tools.
