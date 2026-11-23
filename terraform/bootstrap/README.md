# Terraform Bootstrap

One-time setup to create the foundational AWS resources for the RAG platform.
Run this manually in AWS CloudShell with administrator access.

## What This Creates

1. **S3 Bucket** for Terraform remote state
   - Versioning enabled
   - Server-side encryption (AES256)
   - Public access blocked
   - S3 native lockfile locking (no DynamoDB needed)

2. **GitHub OIDC Provider** for keyless authentication
   - Allows GitHub Actions to assume AWS roles without stored credentials

3. **IAM Roles**
   - `rag-platform-plan`: Read-only access for PRs (terraform plan)
   - `rag-platform-apply`: Write access for main branch only (terraform apply)
   - Both scoped strictly to `repo:WaiteM124/rag-platform`

4. **AWS Budget**
   - $50/month limit
   - Email alerts at 50%, 80%, and 100% thresholds

## Usage

### Prerequisites

- AWS account with administrator access
- AWS CloudShell or local AWS CLI configured

### Run in AWS CloudShell

```bash
# Clone the repository
git clone https://github.com/WaiteM124/rag-platform.git
cd rag-platform/terraform/bootstrap

# Initialize Terraform (uses local state for bootstrap)
terraform init

# Review the plan
terraform plan -var="alert_email=your-email@example.com"

# Apply (enter 'yes' when prompted)
terraform apply -var="alert_email=your-email@example.com"
```

### Configure GitHub Repository Variables

After apply completes, set these repository variables in GitHub:

| Variable | Value (from terraform output) |
|----------|-------------------------------|
| `AWS_REGION` | `eu-west-2` |
| `TF_STATE_BUCKET` | `state_bucket_name` output |
| `AWS_PLAN_ROLE_ARN` | `plan_role_arn` output |
| `AWS_APPLY_ROLE_ARN` | `apply_role_arn` output |

Go to: GitHub repo → Settings → Secrets and variables → Actions → Variables

### Outputs

```bash
# View all outputs
terraform output

# Get specific values
terraform output state_bucket_name
terraform output plan_role_arn
terraform output apply_role_arn
```

## State Management

This bootstrap stack uses **local state** because:
- It's run once manually
- It creates the S3 bucket that stores state for all other stacks
- Circular dependency if it used remote state

Keep the CloudShell session or save the `terraform.tfstate` file securely
if you need to modify the bootstrap resources later.

## Security Notes

- The OIDC trust conditions are scoped to `repo:WaiteM124/rag-platform` only
- Plan role can only read state and describe resources
- Apply role is restricted to main branch pushes only
- No long-lived AWS credentials are stored in GitHub
