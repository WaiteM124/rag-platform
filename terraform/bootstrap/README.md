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
     - `CreateServiceLinkedRole` conditioned on specific AWS services

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

This bootstrap stack uses **local state** because:
- It's run once manually
- It creates the S3 bucket that stores state for all other stacks
- Circular dependency if it used remote state

Keep the CloudShell session or save the `terraform.tfstate` file securely
if you need to modify the bootstrap resources later.

## Security Notes

### OIDC Trust Scoping
- **Plan role**: Trusts only `repo:WaiteM124/rag-platform:pull_request` (PRs only)
- **Apply role**: Trusts only `repo:WaiteM124/rag-platform:environment:production` (requires the GitHub environment)
- No long-lived AWS credentials are stored in GitHub

### IAM Least Privilege
- Role/policy write actions are scoped to `arn:aws:iam::<account>:role/rag-platform-*` and `policy/rag-platform-*`
- **Self-modification denied**: The apply role cannot modify itself or the plan role
- `iam:PassRole` is restricted to `ecs-tasks.amazonaws.com` only
- `CreateServiceLinkedRole` is conditioned on specific AWS services (ECS, RDS, ELB, Application Auto Scaling)

### Why No Permissions Boundary?

A permissions boundary on the CI roles would add defense-in-depth but increases complexity:
- Requires the boundary policy to be created before the roles
- Must be maintained in sync with the actual permissions needed
- Bootstrap would need a two-phase approach

For this dedicated account with scoped IAM permissions and self-modification denied,
the current setup provides adequate protection. A permissions boundary can be added
in a future hardening phase if the account is shared or the threat model changes.

See `docs/build-plan.md` §7 (Threat Model) for the full security analysis.
