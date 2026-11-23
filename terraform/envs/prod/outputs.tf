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
