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

variable "github_owner_id" {
  description = "GitHub owner/org numeric ID (immutable, prevents repo-name reuse attacks)"
  type        = string
  default     = "351398746"
}

variable "github_repo_id" {
  description = "GitHub repository numeric ID (immutable, prevents repo-name reuse attacks)"
  type        = string
  default     = "1468576170"
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

