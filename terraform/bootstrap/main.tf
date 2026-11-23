terraform {
  required_version = ">= 1.10.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      ManagedBy   = "terraform"
      Environment = "bootstrap"
    }
  }
}

locals {
  github_oidc_provider_url = "token.actions.githubusercontent.com"
  state_bucket_name        = "${var.project_name}-tfstate-${data.aws_caller_identity.current.account_id}"
}

data "aws_caller_identity" "current" {}

# -----------------------------------------------------------------------------
# S3 Bucket for Terraform Remote State
# -----------------------------------------------------------------------------

resource "aws_s3_bucket" "tfstate" {
  bucket = local.state_bucket_name

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  rule {
    id     = "cleanup-old-versions"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

# -----------------------------------------------------------------------------
# GitHub OIDC Provider
# -----------------------------------------------------------------------------

resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://${local.github_oidc_provider_url}"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["ffffffffffffffffffffffffffffffffffffffff"]
}

# -----------------------------------------------------------------------------
# IAM Role: Plan (read-only, for PRs)
# -----------------------------------------------------------------------------

data "aws_iam_policy_document" "github_actions_plan_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.github_oidc_provider_url}:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.github_oidc_provider_url}:sub"
      values = [
        "repo:${var.github_org}/${var.github_repo}:pull_request"
      ]
    }
  }
}

resource "aws_iam_role" "github_actions_plan" {
  name               = "${var.project_name}-plan"
  assume_role_policy = data.aws_iam_policy_document.github_actions_plan_trust.json
}

data "aws_iam_policy_document" "github_actions_plan_permissions" {
  statement {
    sid    = "TerraformStateRead"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.tfstate.arn,
      "${aws_s3_bucket.tfstate.arn}/*",
    ]
  }

  statement {
    sid    = "TerraformStateLock"
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = [
      "${aws_s3_bucket.tfstate.arn}/*.tflock",
    ]
  }

  statement {
    sid    = "ReadOnlyAccess"
    effect = "Allow"
    actions = [
      "ec2:Describe*",
      "ec2:Get*",
      "ecs:Describe*",
      "ecs:List*",
      "ecr:Describe*",
      "ecr:GetRepositoryPolicy",
      "ecr:ListImages",
      "rds:Describe*",
      "rds:List*",
      "s3:GetBucket*",
      "s3:List*",
      "iam:GetRole",
      "iam:GetRolePolicy",
      "iam:GetPolicy",
      "iam:GetPolicyVersion",
      "iam:ListAttachedRolePolicies",
      "iam:ListRolePolicies",
      "iam:ListPolicies",
      "iam:ListPolicyVersions",
      "iam:GetOpenIDConnectProvider",
      "secretsmanager:Describe*",
      "secretsmanager:List*",
      "logs:Describe*",
      "logs:List*",
      "elasticloadbalancing:Describe*",
      "application-autoscaling:Describe*",
      "cloudwatch:Describe*",
      "cloudwatch:Get*",
      "cloudwatch:List*",
      "budgets:ViewBudget",
      "budgets:DescribeBudget*",
      "ce:Get*",
      "sts:GetCallerIdentity",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "github_actions_plan" {
  name   = "terraform-plan"
  role   = aws_iam_role.github_actions_plan.id
  policy = data.aws_iam_policy_document.github_actions_plan_permissions.json
}

# -----------------------------------------------------------------------------
# IAM Role: Apply (write access, for main branch only)
# -----------------------------------------------------------------------------

data "aws_iam_policy_document" "github_actions_apply_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.github_oidc_provider_url}:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.github_oidc_provider_url}:sub"
      values = [
        "repo:${var.github_org}/${var.github_repo}:environment:production"
      ]
    }
  }
}

resource "aws_iam_role" "github_actions_apply" {
  name               = "${var.project_name}-apply"
  assume_role_policy = data.aws_iam_policy_document.github_actions_apply_trust.json
}

data "aws_iam_policy_document" "github_actions_apply_permissions" {
  statement {
    sid    = "TerraformState"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.tfstate.arn,
      "${aws_s3_bucket.tfstate.arn}/*",
    ]
  }

  statement {
    sid    = "VPCManagement"
    effect = "Allow"
    actions = [
      "ec2:*Vpc*",
      "ec2:*Subnet*",
      "ec2:*RouteTable*",
      "ec2:*InternetGateway*",
      "ec2:*SecurityGroup*",
      "ec2:*NetworkAcl*",
      "ec2:*Address*",
      "ec2:Describe*",
      "ec2:Get*",
      "ec2:CreateTags",
      "ec2:DeleteTags",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "ECSManagement"
    effect = "Allow"
    actions = [
      "ecs:*",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "ECRManagement"
    effect = "Allow"
    actions = [
      "ecr:*",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "RDSManagement"
    effect = "Allow"
    actions = [
      "rds:*",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "IAMReadOnly"
    effect = "Allow"
    actions = [
      "iam:GetRole",
      "iam:GetRolePolicy",
      "iam:GetPolicy",
      "iam:GetPolicyVersion",
      "iam:ListAttachedRolePolicies",
      "iam:ListRolePolicies",
      "iam:ListPolicyVersions",
      "iam:GetOpenIDConnectProvider",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "IAMRoleManagement"
    effect = "Allow"
    actions = [
      "iam:CreateRole",
      "iam:DeleteRole",
      "iam:UpdateRole",
      "iam:TagRole",
      "iam:UntagRole",
      "iam:PutRolePolicy",
      "iam:DeleteRolePolicy",
      "iam:AttachRolePolicy",
      "iam:DetachRolePolicy",
    ]
    resources = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.project_name}-*",
    ]
  }

  statement {
    sid    = "IAMPolicyManagement"
    effect = "Allow"
    actions = [
      "iam:CreatePolicy",
      "iam:DeletePolicy",
      "iam:CreatePolicyVersion",
      "iam:DeletePolicyVersion",
    ]
    resources = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/${var.project_name}-*",
    ]
  }

  statement {
    sid    = "DenySelfModification"
    effect = "Deny"
    actions = [
      "iam:CreateRole",
      "iam:DeleteRole",
      "iam:UpdateRole",
      "iam:TagRole",
      "iam:UntagRole",
      "iam:PutRolePolicy",
      "iam:DeleteRolePolicy",
      "iam:AttachRolePolicy",
      "iam:DetachRolePolicy",
      "iam:UpdateAssumeRolePolicy",
    ]
    resources = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.project_name}-plan",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.project_name}-apply",
    ]
  }

  statement {
    sid    = "IAMPassRole"
    effect = "Allow"
    actions = [
      "iam:PassRole",
    ]
    resources = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.project_name}-*",
    ]
    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["ecs-tasks.amazonaws.com"]
    }
  }

  statement {
    sid    = "IAMServiceLinkedRoles"
    effect = "Allow"
    actions = [
      "iam:CreateServiceLinkedRole",
    ]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "iam:AWSServiceName"
      values = [
        "ecs.amazonaws.com",
        "rds.amazonaws.com",
        "elasticloadbalancing.amazonaws.com",
        "application-autoscaling.amazonaws.com",
      ]
    }
  }

  statement {
    sid    = "SecretsManager"
    effect = "Allow"
    actions = [
      "secretsmanager:*",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "LoadBalancer"
    effect = "Allow"
    actions = [
      "elasticloadbalancing:*",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:*",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "AutoScaling"
    effect = "Allow"
    actions = [
      "application-autoscaling:*",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "CloudWatch"
    effect = "Allow"
    actions = [
      "cloudwatch:*",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "S3StaticSite"
    effect = "Allow"
    actions = [
      "s3:*",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "CloudFront"
    effect = "Allow"
    actions = [
      "cloudfront:*",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "ACM"
    effect = "Allow"
    actions = [
      "acm:*",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "Route53"
    effect = "Allow"
    actions = [
      "route53:*",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "Budgets"
    effect = "Allow"
    actions = [
      "budgets:*",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "CostExplorer"
    effect = "Allow"
    actions = [
      "ce:*",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "STSIdentity"
    effect = "Allow"
    actions = [
      "sts:GetCallerIdentity",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "github_actions_apply" {
  name   = "terraform-apply"
  role   = aws_iam_role.github_actions_apply.id
  policy = data.aws_iam_policy_document.github_actions_apply_permissions.json
}

# -----------------------------------------------------------------------------
# AWS Budget with Alerts
# -----------------------------------------------------------------------------

resource "aws_budgets_budget" "monthly" {
  name         = "${var.project_name}-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.budget_limit)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    notification_type          = "ACTUAL"
    threshold                  = 50
    threshold_type             = "PERCENTAGE"
    subscriber_email_addresses = [var.alert_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    notification_type          = "ACTUAL"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    subscriber_email_addresses = [var.alert_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    notification_type          = "ACTUAL"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    subscriber_email_addresses = [var.alert_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    notification_type          = "FORECASTED"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    subscriber_email_addresses = [var.alert_email]
  }
}
