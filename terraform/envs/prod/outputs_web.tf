output "alb_dns_name" {
  description = "ALB DNS name (CNAME target in Cloudflare)"
  value       = local.web_enabled ? aws_lb.web[0].dns_name : null
}

output "acm_validation_record_name" {
  description = "ACM DNS validation CNAME name (Cloudflare)"
  value       = local.web_enabled ? tolist(aws_acm_certificate.web[0].domain_validation_options)[0].resource_record_name : null
}

output "acm_validation_record_value" {
  description = "ACM DNS validation CNAME value (Cloudflare)"
  value       = local.web_enabled ? tolist(aws_acm_certificate.web[0].domain_validation_options)[0].resource_record_value : null
}

output "web_ecr_repository_url" {
  description = "ECR repository URL for web image"
  value       = local.web_enabled ? aws_ecr_repository.web[0].repository_url : null
}

output "web_service_name" {
  description = "ECS service name for deployments"
  value       = local.web_enabled ? aws_ecs_service.web[0].name : null
}