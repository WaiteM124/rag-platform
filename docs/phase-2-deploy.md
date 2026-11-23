# Phase 2 deploy: rag.mileswaite.net

DNS is on **Cloudflare** (manual). Terraform does **not** create Route 53 records.

## Two-step HTTPS

1. **`enable_https = false` (default)**  
   - `terraform apply` creates the ALB, ECS service, and ACM certificate (pending validation).  
   - Outputs: `alb_dns_name`, `acm_validation_record_name`, `acm_validation_record_value`.  
   - In Cloudflare: add the ACM validation CNAME, then a CNAME `rag` → `alb_dns_name` (proxied or DNS-only).  
   - Wait until ACM shows the certificate as **Issued** (console).

2. **`enable_https = true`**  
   - Set `enable_https = true` in prod tfvars (or variable) and apply again.  
   - HTTP listener returns 301 → HTTPS; HTTPS uses `ELBSecurityPolicy-TLS13-1-2-2021-06`.  
   - Set ECS env `HTTPS_ENABLED=true` (Terraform sets this when `enable_https` is true).

## Langfuse

Secret `rag-platform/langfuse` is created with empty JSON keys. After adding real keys in Secrets Manager, restart the ECS service (or redeploy). The app enables tracing only when both keys are non-empty.