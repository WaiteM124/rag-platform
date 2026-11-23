variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "eu-west-2"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "rag-platform"
}

variable "github_org" {
  description = "GitHub organization or username"
  type        = string
  default     = "WaiteM124"
}

variable "github_repo" {
  description = "GitHub repository name"
  type        = string
  default     = "rag-platform"
}

variable "alert_email" {
  description = "Email address for budget alerts"
  type        = string
  sensitive   = true
}

variable "budget_limit" {
  description = "Monthly budget limit in USD"
  type        = number
  default     = 50
}

variable "aws_account_id" {
  description = "AWS account ID (used in examples/documentation only)"
  type        = string
  default     = "762771090975"
}
