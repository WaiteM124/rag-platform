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

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "enable_vpc" {
  description = "Whether to create VPC resources (set false for cost-free first apply)"
  type        = bool
  default     = true
}

variable "enable_rds" {
  description = "Whether to create RDS resources (disabled for Phase 0)"
  type        = bool
  default     = false
}

variable "enable_ecs" {
  description = "Whether to create ECS resources (disabled for Phase 0)"
  type        = bool
  default     = false
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}
