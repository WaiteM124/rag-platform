# -----------------------------------------------------------------------------
# RDS PostgreSQL 16 + pgvector (migrations applied by ingest task)
# -----------------------------------------------------------------------------

resource "aws_db_parameter_group" "postgres16" {
  count = var.enable_rds ? 1 : 0

  name        = "${local.name_prefix}-pg16"
  family      = "postgres16"
  description = "PostgreSQL 16 for ${local.name_prefix}"

  tags = {
    Name = "${local.name_prefix}-pg16-params"
  }
}

resource "aws_db_instance" "main" {
  count = var.enable_rds && var.enable_vpc ? 1 : 0

  identifier     = "${local.name_prefix}-postgres"
  engine         = "postgres"
  engine_version = "16"
  instance_class = var.rds_instance_class

  allocated_storage = var.rds_allocated_storage_gb
  storage_type      = "gp3"

  db_name  = var.rds_database_name
  username = var.rds_master_username
  port     = 5432

  manage_master_user_password = true

  db_subnet_group_name   = aws_db_subnet_group.main[0].name
  vpc_security_group_ids = [module.network[0].rds_security_group_id]
  publicly_accessible    = false
  multi_az               = false

  parameter_group_name = aws_db_parameter_group.postgres16[0].name

  storage_encrypted         = true
  backup_retention_period   = 7
  deletion_protection       = true
  skip_final_snapshot       = false
  final_snapshot_identifier = "${local.name_prefix}-postgres-final"

  apply_immediately = false

  tags = {
    Name = "${local.name_prefix}-postgres"
  }
}