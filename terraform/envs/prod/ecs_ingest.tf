# -----------------------------------------------------------------------------
# ECS cluster, ECR, ingest task (Fargate, public subnet, assignPublicIp)
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "ingest" {
  count = var.enable_ecs ? 1 : 0

  name              = "/ecs/${local.name_prefix}-ingest"
  retention_in_days = 14

  tags = {
    Name = "${local.name_prefix}-ingest-logs"
  }
}

resource "aws_ecr_repository" "ingest" {
  count = var.enable_ecs ? 1 : 0

  name                 = "${var.project_name}-ingest"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.project_name}-ingest"
  }
}

resource "aws_ecr_lifecycle_policy" "ingest" {
  count = var.enable_ecs ? 1 : 0

  repository = aws_ecr_repository.ingest[0].name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      },
    ]
  })
}

resource "aws_iam_role" "ingest_task_execution" {
  count = var.enable_ecs ? 1 : 0

  name = "${var.project_name}-ingest-task-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      },
    ]
  })

  tags = {
    Name = "${var.project_name}-ingest-task-execution"
  }
}

resource "aws_iam_role_policy_attachment" "ingest_task_execution" {
  count = var.enable_ecs ? 1 : 0

  role       = aws_iam_role.ingest_task_execution[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

data "aws_iam_policy_document" "ingest_task_execution_secrets" {
  count = var.enable_ecs && var.enable_rds ? 1 : 0

  statement {
    sid    = "RdsMasterSecret"
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret",
    ]
    resources = compact([
      try(aws_db_instance.main[0].master_user_secret[0].secret_arn, null),
    ])
  }
}

resource "aws_iam_role_policy" "ingest_task_execution_secrets" {
  count = var.enable_ecs && var.enable_rds ? 1 : 0

  name   = "rds-secret-read"
  role   = aws_iam_role.ingest_task_execution[0].id
  policy = data.aws_iam_policy_document.ingest_task_execution_secrets[0].json
}

resource "aws_iam_role" "ingest_task" {
  count = var.enable_ecs ? 1 : 0

  name = "${var.project_name}-ingest-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      },
    ]
  })

  tags = {
    Name = "${var.project_name}-ingest-task"
  }
}

data "aws_iam_policy_document" "ingest_task" {
  count = var.enable_ecs ? 1 : 0

  statement {
    sid    = "BedrockInvoke"
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
    ]
    resources = local.bedrock_invoke_arns
  }

  dynamic "statement" {
    for_each = var.enable_rds ? [1] : []
    content {
      sid    = "RdsMasterSecret"
      effect = "Allow"
      actions = [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret",
      ]
      resources = compact([
        try(aws_db_instance.main[0].master_user_secret[0].secret_arn, null),
      ])
    }
  }
}

resource "aws_iam_role_policy" "ingest_task" {
  count = var.enable_ecs ? 1 : 0

  name   = "ingest-task"
  role   = aws_iam_role.ingest_task[0].id
  policy = data.aws_iam_policy_document.ingest_task[0].json
}

resource "aws_ecs_task_definition" "ingest" {
  count = var.enable_ecs && var.enable_vpc && var.enable_rds ? 1 : 0

  family                   = "${local.name_prefix}-ingest"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.ingest_task_cpu
  memory                   = var.ingest_task_memory

  execution_role_arn = aws_iam_role.ingest_task_execution[0].arn
  task_role_arn      = aws_iam_role.ingest_task[0].arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "ARM64"
  }

  container_definitions = jsonencode([
    {
      name      = "ingest"
      image     = "${aws_ecr_repository.ingest[0].repository_url}:latest"
      essential = true
      command   = ["python", "-m", "ingest", "run", "--collection", "complex-systems"]

      environment = [
        { name = "AWS_REGION", value = var.aws_region },
        { name = "RAG_DB_HOST", value = aws_db_instance.main[0].address },
        { name = "RAG_DB_PORT", value = tostring(aws_db_instance.main[0].port) },
        { name = "RAG_DB_NAME", value = var.rds_database_name },
        { name = "RAG_EMBEDDING_MODEL_ID", value = var.bedrock_embedding_model_id },
        { name = "RAG_COLLECTION", value = "complex-systems" },
        {
          name  = "RAG_DB_SECRET_ARN"
          value = aws_db_instance.main[0].master_user_secret[0].secret_arn
        },
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ingest[0].name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ingest"
        }
      }
    },
  ])

  tags = {
    Name = "${local.name_prefix}-ingest"
  }

  depends_on = [
    aws_cloudwatch_log_group.ingest,
  ]
}