output "vpc_id" {
  description = "VPC ID"
  value       = var.enable_vpc ? module.network[0].vpc_id : null
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = var.enable_vpc ? module.network[0].public_subnet_ids : []
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = var.enable_vpc ? module.network[0].private_subnet_ids : []
}

output "account_id" {
  description = "AWS account ID"
  value       = data.aws_caller_identity.current.account_id
}

output "region" {
  description = "AWS region"
  value       = var.aws_region
}

output "environment" {
  description = "Environment name"
  value       = var.environment
}

output "db_subnet_group_name" {
  description = "RDS subnet group name"
  value       = var.enable_rds && var.enable_vpc ? aws_db_subnet_group.main[0].name : null
}

output "ecs_cluster_arn" {
  description = "ECS cluster ARN"
  value       = var.enable_ecs ? aws_ecs_cluster.main[0].arn : null
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = var.enable_ecs ? aws_ecs_cluster.main[0].name : null
}

output "ingest_ecr_repository_url" {
  description = "ECR repository URL for ingest image"
  value       = var.enable_ecs ? aws_ecr_repository.ingest[0].repository_url : null
}

output "ingest_task_definition_arn" {
  description = "ECS task definition ARN for ingest runs"
  value       = var.enable_ecs && var.enable_rds ? try(aws_ecs_task_definition.ingest[0].arn, null) : null
}

output "ingest_task_execution_role_arn" {
  description = "ECS task execution role for ingest"
  value       = var.enable_ecs ? aws_iam_role.ingest_task_execution[0].arn : null
}

output "ingest_task_role_arn" {
  description = "ECS task role for ingest"
  value       = var.enable_ecs ? aws_iam_role.ingest_task[0].arn : null
}

output "ecs_tasks_security_group_id" {
  description = "Security group for Fargate ingest tasks"
  value       = var.enable_vpc ? module.network[0].ecs_tasks_security_group_id : null
}

output "rds_endpoint" {
  description = "RDS hostname (private)"
  value       = var.enable_rds ? try(aws_db_instance.main[0].address, null) : null
  sensitive   = false
}
