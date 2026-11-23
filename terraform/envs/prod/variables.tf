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
  description = "Whether to create RDS resources"
  type        = bool
  default     = true
}

variable "enable_ecs" {
  description = "Whether to create ECS resources (ingest Fargate task)"
  type        = bool
  default     = true
}

variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.micro"
}

variable "rds_allocated_storage_gb" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 20
}

variable "rds_backup_retention_days" {
  description = "RDS automated backup retention (days). Free Tier allows 1; use 7 after Paid plan."
  type        = number
  default     = 1

  validation {
    condition     = var.rds_backup_retention_days >= 0 && var.rds_backup_retention_days <= 35
    error_message = "rds_backup_retention_days must be between 0 and 35."
  }
}

variable "rds_database_name" {
  description = "Initial database name"
  type        = string
  default     = "ragplatform"
}

variable "rds_master_username" {
  description = "RDS master username"
  type        = string
  default     = "ragadmin"
}

variable "bedrock_answer_model_id" {
  description = "Bedrock model / inference profile ID for answers"
  type        = string
  default     = "qwen.qwen3-235b-a22b-2507-v1:0"
}

variable "bedrock_eval_judge_model_id" {
  description = "Bedrock model / inference profile ID for eval judge"
  type        = string
  default     = "deepseek.v3.2"
}

variable "bedrock_embedding_model_id" {
  description = "Bedrock embedding model ID (Titan Text Embeddings V2, 1024-d)"
  type        = string
  default     = "amazon.titan-embed-text-v2:0"
}

variable "ingest_task_cpu" {
  description = "Fargate CPU units for ingest task"
  type        = string
  default     = "512"
}

variable "ingest_task_memory" {
  description = "Fargate memory (MiB) for ingest task"
  type        = string
  default     = "1024"
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}
