# Terraform Infrastructure

All AWS infrastructure is managed via Terraform with remote state in S3.

## Structure

```
terraform/
├── bootstrap/           # One-time setup (run manually in CloudShell)
│   ├── main.tf          # S3 state bucket, GitHub OIDC, IAM roles, Budget
│   ├── variables.tf
│   └── outputs.tf
├── envs/
│   └── prod/            # Production environment
│       ├── backend.tf   # S3 remote state configuration
│       ├── main.tf      # Root module composition
│       ├── variables.tf
│       └── outputs.tf
└── modules/
    └── network/         # VPC, subnets, security groups (no NAT)
```

## Bootstrap (One-Time Setup)

See `bootstrap/README.md` for CloudShell instructions.

## CI/CD

- **PR**: `terraform fmt -check`, `validate`, `tflint`, `plan` (via OIDC plan role)
- **main**: `terraform apply` (via OIDC apply role)

No long-lived AWS credentials are stored in GitHub.
