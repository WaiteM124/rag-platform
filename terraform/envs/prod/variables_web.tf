variable "enable_web" {
  description = "Whether to deploy the public web/API ECS service behind ALB"
  type        = bool
  default     = true
}

variable "domain_name" {
  description = "Public hostname (ACM cert, Cloudflare DNS manual)"
  type        = string
  default     = "rag.mileswaite.net"
}

variable "enable_https" {
  description = "HTTPS listener with ACM cert (set true after DNS validation)"
  type        = bool
  default     = false
}

variable "web_task_cpu" {
  description = "Fargate CPU for web task (256 = 0.25 vCPU)"
  type        = string
  default     = "256"
}

variable "web_task_memory" {
  description = "Fargate memory MiB for web task"
  type        = string
  default     = "512"
}

variable "daily_spend_cap_gbp" {
  description = "Application daily spend cap (GBP)"
  type        = string
  default     = "2.00"
}