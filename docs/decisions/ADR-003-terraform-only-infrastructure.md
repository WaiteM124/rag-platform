# ADR-003: Terraform-only AWS infrastructure

**Status:** Accepted  
**Date:** 2026-11-24  

---

## Context

The platform runs on AWS (VPC, RDS, ECS Fargate, ALB, ECR, Secrets Manager, IAM via GitHub OIDC). Console drift would break reproducibility and the portfolio narrative of production-grade IaC.

## Decision

All infrastructure is declared in Terraform:

- `terraform/bootstrap/` — one-time CloudShell apply (S3 state, OIDC provider, plan/apply/eval roles, budget).
- `terraform/envs/prod/` — ongoing production stack.
- `terraform/modules/` — shared modules (e.g. network).

CI (`.github/workflows/terraform.yml`) formats, validates, runs tflint, plans on PRs (plan role), and applies on `main` with the GitHub `production` environment (apply role). Secrets (DB, Langfuse keys, etc.) are created or referenced in Terraform and filled in Secrets Manager — never committed. Prefer `data.aws_caller_identity` over hardcoded AWS account IDs.

Deploy Web chains from a successful Terraform workflow on `main` (or manual dispatch).

## Consequences

- No console-created resources (except documented secret *values* and external DNS in Cloudflare).
- Changes under `terraform/**` trigger Terraform CI and can cascade to deploy — keep infra PRs intentional.
- Agents must not trigger apply/deploy/ingest workflows without Miles's go-ahead.
- Bootstrap remains a privileged, rare operation; day-to-day changes go through `envs/prod`.
