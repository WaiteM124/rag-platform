# Network Module

VPC configuration for the RAG platform.

## Design Principles

- **No NAT Gateway** - Fargate tasks run in public subnets with security groups locked to ALB
- **Private subnets** for RDS (database isolated from internet)
- **VPC endpoints** only where clearly cost-effective

## Resources

- VPC with DNS hostnames enabled
- 2 public subnets (Fargate tasks, ALB)
- 2 private subnets (RDS)
- Internet Gateway
- Security groups with least-privilege rules

## Cost Consideration

NAT Gateway would cost ~$36.50/month minimum. By using public subnets with
tight security groups, we save this cost while maintaining security through:
- Security group rules allowing only ALB → Fargate traffic
- No inbound internet access to tasks (only outbound for API calls)
