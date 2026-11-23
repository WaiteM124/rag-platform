output "state_bucket_name" {
  description = "S3 bucket name for Terraform remote state"
  value       = aws_s3_bucket.tfstate.id
}

output "state_bucket_arn" {
  description = "S3 bucket ARN for Terraform remote state"
  value       = aws_s3_bucket.tfstate.arn
}

output "plan_role_arn" {
  description = "IAM role ARN for GitHub Actions terraform plan (PRs)"
  value       = aws_iam_role.github_actions_plan.arn
}

output "apply_role_arn" {
  description = "IAM role ARN for GitHub Actions terraform apply (main branch)"
  value       = aws_iam_role.github_actions_apply.arn
}

output "github_oidc_provider_arn" {
  description = "GitHub OIDC provider ARN"
  value       = aws_iam_openid_connect_provider.github.arn
}

output "budget_name" {
  description = "AWS Budget name"
  value       = aws_budgets_budget.monthly.name
}

output "github_variables_to_set" {
  description = "GitHub repository variables to configure"
  value = {
    AWS_REGION         = var.aws_region
    TF_STATE_BUCKET    = aws_s3_bucket.tfstate.id
    AWS_PLAN_ROLE_ARN  = aws_iam_role.github_actions_plan.arn
    AWS_APPLY_ROLE_ARN = aws_iam_role.github_actions_apply.arn
  }
}
