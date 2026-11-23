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
