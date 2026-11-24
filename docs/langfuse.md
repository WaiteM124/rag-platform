# Langfuse tracing (Cloud EU)

The public web service emits one Langfuse **trace per `/api/ask` request** with nested
child spans for each stage (`query_embedding`, `vector_retrieval`, `prompt_build`,
`generation`, `output_guard`). Generation observations carry model id, token usage,
and cost when prices are verified.

Tracing is a **strict no-op** when `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` are
empty or invalid — request handling never depends on Langfuse.

## Owner setup (after merging this change)

1. **Create a Langfuse Cloud EU project**
   - Go to [https://cloud.langfuse.com](https://cloud.langfuse.com) (EU host).
   - Create an organisation/project for this portfolio demo.

2. **Create API keys**
   - In the project: Settings → API Keys → Create.
   - Copy the **public** key and **secret** key.

3. **Put each value into Secrets Manager** (eu-west-2)
   - Secret name `rag-platform-prod/langfuse-public-key` → paste the public key as the
     secret **string** value (plain text, not JSON).
   - Secret name `rag-platform-prod/langfuse-secret-key` → paste the secret key as the
     secret **string** value.
   - Terraform creates these secrets with a `REPLACE_ME` placeholder and
     `lifecycle.ignore_changes` on the value, so console edits are not overwritten.

4. **Run Terraform Apply** (prod) so the web task definition gains:
   - env `LANGFUSE_HOST=https://cloud.langfuse.com`
   - secrets `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` from the two ARNs
   - execution-role `secretsmanager:GetSecretValue` on just those ARNs (+ DB secret)

5. **Run Deploy Web** (`workflow_dispatch` or via the Terraform → Deploy Web chain)
   so ECS tasks pick up the new task definition revision and secrets.

6. **Verify**
   - Ask a question on https://rag.mileswaite.net
   - Confirm a nested trace appears in Langfuse
   - Confirm CloudWatch Logs for the web task show one JSON line per request with
     `event":"rag_request_metrics"` (no question/answer text)

Never commit Langfuse keys, AWS account IDs, or secret ARNs with account numbers.
