# Terraform Bootstrap

One-time setup to create the foundational AWS resources for the RAG platform.
Run this manually in AWS CloudShell with administrator access.

## What This Creates

1. **S3 Bucket** for Terraform remote state
   - Versioning enabled
   - Server-side encryption (AES256)
   - Public access blocked
   - S3 native lockfile locking (requires Terraform >= 1.10.0, no DynamoDB needed)

2. **GitHub OIDC Provider** for keyless authentication
   - Allows GitHub Actions to assume AWS roles without stored credentials

3. **IAM Roles** (least-privilege, scoped to `rag-platform-*` resources)
   - `rag-platform-plan`: Read-only access for PRs (terraform plan)
     - Trust: `repo:WaiteM124/rag-platform:pull_request` only
   - `rag-platform-apply`: Write access for production deploys
     - Trust: `repo:WaiteM124/rag-platform:environment:production` only
     - IAM write actions scoped to `arn:aws:iam::<account>:role/rag-platform-*` and `policy/rag-platform-*`
     - Explicit Deny on modifying the plan/apply roles themselves
     - `iam:PassRole` restricted to ECS tasks only
     - `CreateServiceLinkedRole` conditioned on specific AWS services (including ECS Application Auto Scaling)

4. **AWS Budget**
   - $50/month limit (covers entire dedicated account)
   - Email alerts at 50%, 80%, 100% (ACTUAL) and 100% (FORECASTED)

## Usage

### Prerequisites

- AWS account with administrator access
- AWS CloudShell or local AWS CLI configured
- Terraform >= 1.10.0 (for S3 lockfile support)

### Run in AWS CloudShell

CloudShell's bundled Terraform may be outdated. Install the required version first:

```bash
# Install Terraform 1.17.2 into ~/bin
mkdir -p ~/bin
curl -fsSL https://releases.hashicorp.com/terraform/1.17.2/terraform_1.17.2_linux_amd64.zip -o /tmp/terraform.zip
unzip -o /tmp/terraform.zip -d ~/bin
rm /tmp/terraform.zip
export PATH="$HOME/bin:$PATH"

# Verify version
terraform version
# Should show: Terraform v1.17.2

# Clone the repository
git clone https://github.com/WaiteM124/rag-platform.git
cd rag-platform/terraform/bootstrap

# Initialize Terraform (uses local state for bootstrap)
terraform init

# Review the plan
terraform plan -var="alert_email=your-email@example.com"

# Apply (enter 'yes' when prompted)
terraform apply -var="alert_email=your-email@example.com"

# View outputs
terraform output
```

### Configure GitHub Repository

After bootstrap completes, configure GitHub in two steps:

#### 1. Create the `production` Environment

The apply role trusts only the `production` environment. You **must** create it:

1. Go to: **GitHub repo → Settings → Environments → New environment**
2. Name: `production`
3. Configure protection rules:
   - **Deployment branches**: Select "Selected branches" → Add `main`
   - **Required reviewers** (optional): Add reviewers for manual approval before apply
4. Click **Save protection rules**

#### 2. Set Repository Variables

Go to: **GitHub repo → Settings → Secrets and variables → Actions → Variables**

| Variable | Value (from terraform output) |
|----------|-------------------------------|
| `AWS_REGION` | `eu-west-2` |
| `TF_STATE_BUCKET` | `terraform output state_bucket_name` |
| `AWS_PLAN_ROLE_ARN` | `terraform output plan_role_arn` |
| `AWS_APPLY_ROLE_ARN` | `terraform output apply_role_arn` |

### Outputs

```bash
# View all outputs
terraform output

# Get specific values for GitHub variables
terraform output state_bucket_name
terraform output plan_role_arn
terraform output apply_role_arn
```

## State Management

This bootstrap stack uses **local state** (`terraform.tfstate` in this directory) because:
- It's run once manually
- It creates the S3 bucket that stores state for all other stacks
- Circular dependency if it used remote state

**Terraform >= 1.10.0 is required** (see `required_version` in `main.tf`); older CLI versions cannot use S3 native lockfile locking used by the other stacks.

### CloudShell state loss

AWS CloudShell wipes your home directory (including clone, `.terraform/`, and `terraform.tfstate`) after a period of inactivity. If bootstrap was already applied successfully, the AWS resources still exist—you only lost local state. Do **not** run `terraform apply` again on a fresh CloudShell session without recovering state, or Terraform will try to recreate resources and fail.

### Recovering state with `terraform import`

After `terraform init`, import existing resources (replace placeholders with your values from the AWS console or CLI):

| Terraform address | Import ID |
|-------------------|-----------|
| `aws_s3_bucket.tfstate` | `<project_name>-tfstate-<ACCOUNT_ID>` (e.g. `rag-platform-tfstate-123456789012`) |
| `aws_s3_bucket_versioning.tfstate` | Same bucket name |
| `aws_s3_bucket_server_side_encryption_configuration.tfstate` | Same bucket name |
| `aws_s3_bucket_public_access_block.tfstate` | Same bucket name |
| `aws_s3_bucket_lifecycle_configuration.tfstate` | Same bucket name |
| `aws_iam_openid_connect_provider.github` | `arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com` |
| `aws_iam_role.github_actions_plan` | `<project_name>-plan` |
| `aws_iam_role_policy.github_actions_plan` | `<project_name>-plan:terraform-plan` |
| `aws_iam_role.github_actions_apply` | `<project_name>-apply` |
| `aws_iam_role_policy.github_actions_apply` | `<project_name>-apply:terraform-apply` |
| `aws_iam_role.github_actions_eval` | `<project_name>-eval` |
| `aws_iam_role_policy.github_actions_eval` | `<project_name>-eval:bedrock-eval` |
| `aws_budgets_budget.monthly` | `<ACCOUNT_ID>:<project_name>-monthly` |

Example (default `project_name` is `rag-platform`):

```bash
export PATH="$HOME/bin:$PATH"   # if using a user-installed Terraform >= 1.10
cd rag-platform/terraform/bootstrap
terraform init

BUCKET="rag-platform-tfstate-123456789012"
ACCOUNT_ID="123456789012"

terraform import aws_s3_bucket.tfstate "$BUCKET"
terraform import aws_s3_bucket_versioning.tfstate "$BUCKET"
terraform import aws_s3_bucket_server_side_encryption_configuration.tfstate "$BUCKET"
terraform import aws_s3_bucket_public_access_block.tfstate "$BUCKET"
terraform import aws_s3_bucket_lifecycle_configuration.tfstate "$BUCKET"
terraform import aws_iam_openid_connect_provider.github "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"
terraform import aws_iam_role.github_actions_plan rag-platform-plan
terraform import aws_iam_role_policy.github_actions_plan rag-platform-plan:terraform-plan
terraform import aws_iam_role.github_actions_apply rag-platform-apply
terraform import aws_iam_role_policy.github_actions_apply rag-platform-apply:terraform-apply
terraform import aws_iam_role.github_actions_eval rag-platform-eval
terraform import aws_iam_role_policy.github_actions_eval rag-platform-eval:bedrock-eval
terraform import aws_budgets_budget.monthly "${ACCOUNT_ID}:rag-platform-monthly"

terraform plan -var="alert_email=your-email@example.com"
# Expect no changes (or only drift you intend to fix)
```

Keep a backup of `terraform.tfstate` somewhere secure (e.g. encrypted object storage) after a successful apply if you plan to change bootstrap later without repeating imports.

## Security Notes

### OIDC Trust Scoping
- **Plan role**: Trusts only `repo:WaiteM124@351398746/rag-platform@1468576170:pull_request`
- **Apply role**: Trusts only `repo:WaiteM124@351398746/rag-platform@1468576170:environment:production`
- **Immutable ID pinning**: GitHub's OIDC `sub` claim embeds numeric owner and repo IDs (e.g., `@351398746`, `@1468576170`). These IDs are immutable—even if someone deletes and recreates a repo with the same name, the new repo gets a different ID. Pinning these IDs in the trust policy prevents repo-name reuse attacks where an attacker could create a repo with the same name after the original is deleted.
- No long-lived AWS credentials are stored in GitHub

### IAM Least Privilege
- Role/policy write actions are scoped to `arn:aws:iam::<account>:role/rag-platform-*` and `policy/rag-platform-*`
- **Self-modification denied**: The apply role cannot modify itself or the plan role
- `iam:PassRole` is restricted to `ecs-tasks.amazonaws.com` only
- `CreateServiceLinkedRole` is conditioned on specific AWS services (ECS, ECS Application Auto Scaling, RDS, ELB, Application Auto Scaling)

### Why No Permissions Boundary?

A permissions boundary on the CI roles would add defense-in-depth but increases complexity:
- Requires the boundary policy to be created before the roles
- Must be maintained in sync with the actual permissions needed
- Bootstrap would need a two-phase approach

For this dedicated account with scoped IAM permissions and self-modification denied,
the current setup provides adequate protection. A permissions boundary can be added
in a future hardening phase if the account is shared or the threat model changes.

See `docs/build-plan.md` §7 (Threat Model) for the full security analysis.
