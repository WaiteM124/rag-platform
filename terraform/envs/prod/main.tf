terraform {
  required_version = ">= 1.10.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = merge(
      {
        Project     = var.project_name
        Environment = var.environment
        ManagedBy   = "terraform"
      },
      var.common_tags
    )
  }
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  azs = ["${var.aws_region}a", "${var.aws_region}b"]

  public_subnets = [
    cidrsubnet(var.vpc_cidr, 8, 1),
    cidrsubnet(var.vpc_cidr, 8, 2),
  ]

  private_subnets = [
    cidrsubnet(var.vpc_cidr, 8, 11),
    cidrsubnet(var.vpc_cidr, 8, 12),
  ]
}

data "aws_caller_identity" "current" {}

# -----------------------------------------------------------------------------
# VPC
# -----------------------------------------------------------------------------

module "network" {
  source = "../../modules/network"
  count  = var.enable_vpc ? 1 : 0

  name_prefix     = local.name_prefix
  vpc_cidr        = var.vpc_cidr
  azs             = local.azs
  public_subnets  = local.public_subnets
  private_subnets = local.private_subnets
}

# -----------------------------------------------------------------------------
# RDS (Phase 1+)
# -----------------------------------------------------------------------------

resource "aws_db_subnet_group" "main" {
  count = var.enable_rds && var.enable_vpc ? 1 : 0

  name        = "${local.name_prefix}-db"
  description = "Database subnet group for ${local.name_prefix}"
  subnet_ids  = module.network[0].private_subnet_ids

  tags = {
    Name = "${local.name_prefix}-db-subnet-group"
  }
}

# -----------------------------------------------------------------------------
# ECS (Phase 2+)
# -----------------------------------------------------------------------------

resource "aws_ecs_cluster" "main" {
  count = var.enable_ecs ? 1 : 0

  name = "${local.name_prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name = "${local.name_prefix}-cluster"
  }
}
