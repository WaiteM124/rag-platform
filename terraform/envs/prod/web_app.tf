# -----------------------------------------------------------------------------
# Public web/API: ALB, ACM (no Route53), ECS Fargate service
# -----------------------------------------------------------------------------

locals {
  web_enabled = var.enable_web && var.enable_ecs && var.enable_vpc && var.enable_rds
}

resource "aws_secretsmanager_secret" "langfuse" {
  count = local.web_enabled ? 1 : 0

  name        = "${var.project_name}/langfuse"
  description = "Langfuse keys (empty until filled manually)"

  tags = {
    Name = "${var.project_name}-langfuse"
  }
}

resource "aws_secretsmanager_secret_version" "langfuse_placeholder" {
  count = local.web_enabled ? 1 : 0

  secret_id = aws_secretsmanager_secret.langfuse[0].id
  secret_string = jsonencode({
    LANGFUSE_PUBLIC_KEY = ""
    LANGFUSE_SECRET_KEY = ""
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}

resource "aws_acm_certificate" "web" {
  count = local.web_enabled ? 1 : 0

  domain_name       = var.domain_name
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "${local.name_prefix}-web-cert"
  }
}

resource "aws_lb" "web" {
  count = local.web_enabled ? 1 : 0

  name               = "${local.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [module.network[0].alb_security_group_id]
  subnets            = module.network[0].public_subnet_ids

  tags = {
    Name = "${local.name_prefix}-alb"
  }
}

resource "aws_lb_target_group" "web" {
  count = local.web_enabled ? 1 : 0

  name        = "${local.name_prefix}-web"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = module.network[0].vpc_id
  target_type = "ip"

  health_check {
    path                = "/healthz"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    matcher             = "200"
  }

  tags = {
    Name = "${local.name_prefix}-web-tg"
  }
}

resource "aws_lb_listener" "http" {
  count = local.web_enabled ? 1 : 0

  load_balancer_arn = aws_lb.web[0].arn
  port              = 80
  protocol          = "HTTP"

  dynamic "default_action" {
    for_each = var.enable_https ? [1] : []
    content {
      type = "redirect"
      redirect {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }
  }

  dynamic "default_action" {
    for_each = var.enable_https ? [] : [1]
    content {
      type             = "forward"
      target_group_arn = aws_lb_target_group.web[0].arn
    }
  }
}

resource "aws_lb_listener" "https" {
  count = local.web_enabled && var.enable_https ? 1 : 0

  load_balancer_arn = aws_lb.web[0].arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate.web[0].arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web[0].arn
  }
}

resource "aws_cloudwatch_log_group" "web" {
  count = local.web_enabled ? 1 : 0

  name              = "/ecs/${local.name_prefix}-web"
  retention_in_days = 14
}

resource "aws_ecr_repository" "web" {
  count = local.web_enabled ? 1 : 0

  name                 = "${var.project_name}-web"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "web" {
  count = local.web_enabled ? 1 : 0

  repository = aws_ecr_repository.web[0].name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 10 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}

resource "aws_iam_role" "web_task_execution" {
  count = local.web_enabled ? 1 : 0

  name = "${var.project_name}-web-task-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "web_task_execution" {
  count = local.web_enabled ? 1 : 0

  role       = aws_iam_role.web_task_execution[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

data "aws_iam_policy_document" "web_task_execution_secrets" {
  count = local.web_enabled ? 1 : 0

  statement {
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret",
    ]
    resources = compact([
      aws_db_instance.main[0].master_user_secret[0].secret_arn,
      aws_secretsmanager_secret.langfuse[0].arn,
    ])
  }
}

resource "aws_iam_role_policy" "web_task_execution_secrets" {
  count = local.web_enabled ? 1 : 0

  name   = "secrets"
  role   = aws_iam_role.web_task_execution[0].id
  policy = data.aws_iam_policy_document.web_task_execution_secrets[0].json
}

resource "aws_iam_role" "web_task" {
  count = local.web_enabled ? 1 : 0

  name = "${var.project_name}-web-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

data "aws_iam_policy_document" "web_task" {
  count = local.web_enabled ? 1 : 0

  statement {
    sid    = "BedrockInvoke"
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
    ]
    resources = local.bedrock_invoke_arns
  }

  statement {
    sid    = "SecretsRead"
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret",
    ]
    resources = compact([
      aws_db_instance.main[0].master_user_secret[0].secret_arn,
      aws_secretsmanager_secret.langfuse[0].arn,
    ])
  }

  statement {
    sid       = "EmitMetrics"
    effect    = "Allow"
    actions   = ["cloudwatch:PutMetricData"]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "cloudwatch:namespace"
      values   = ["RagPlatform"]
    }
  }
}

resource "aws_iam_role_policy" "web_task" {
  count = local.web_enabled ? 1 : 0

  name   = "web-task"
  role   = aws_iam_role.web_task[0].id
  policy = data.aws_iam_policy_document.web_task[0].json
}

resource "aws_ecs_task_definition" "web" {
  count = local.web_enabled ? 1 : 0

  family                   = "${local.name_prefix}-web"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.web_task_cpu
  memory                   = var.web_task_memory
  execution_role_arn       = aws_iam_role.web_task_execution[0].arn
  task_role_arn            = aws_iam_role.web_task[0].arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "ARM64"
  }

  container_definitions = jsonencode([{
    name         = "web"
    image        = "${aws_ecr_repository.web[0].repository_url}:latest"
    essential    = true
    portMappings = [{ containerPort = 8000, protocol = "tcp" }]
    environment = [
      { name = "AWS_REGION", value = var.aws_region },
      { name = "RAG_DB_HOST", value = aws_db_instance.main[0].address },
      { name = "RAG_DB_PORT", value = tostring(aws_db_instance.main[0].port) },
      { name = "RAG_DB_NAME", value = var.rds_database_name },
      { name = "RAG_ANSWER_MODEL_ID", value = var.bedrock_answer_model_id },
      { name = "RAG_EMBEDDING_MODEL_ID", value = var.bedrock_embedding_model_id },
      { name = "DAILY_SPEND_CAP_GBP", value = var.daily_spend_cap_gbp },
      { name = "HTTPS_ENABLED", value = var.enable_https ? "true" : "false" },
      { name = "RAG_DB_SECRET_ARN", value = aws_db_instance.main[0].master_user_secret[0].secret_arn },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.web[0].name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "web"
      }
    }
  }])
}

resource "aws_ecs_service" "web" {
  count = local.web_enabled ? 1 : 0

  name            = "${local.name_prefix}-web"
  cluster         = aws_ecs_cluster.main[0].id
  task_definition = aws_ecs_task_definition.web[0].arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = module.network[0].public_subnet_ids
    security_groups  = [module.network[0].ecs_tasks_security_group_id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.web[0].arn
    container_name   = "web"
    container_port   = 8000
  }

  lifecycle {
    ignore_changes = [task_definition]
  }
}

resource "aws_appautoscaling_target" "web" {
  count = local.web_enabled ? 1 : 0

  max_capacity       = 2
  min_capacity       = 1
  resource_id        = "service/${aws_ecs_cluster.main[0].name}/${aws_ecs_service.web[0].name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "web_cpu" {
  count = local.web_enabled ? 1 : 0

  name               = "${local.name_prefix}-web-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.web[0].resource_id
  scalable_dimension = aws_appautoscaling_target.web[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.web[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70.0
    scale_in_cooldown  = 120
    scale_out_cooldown = 60
  }
}

resource "aws_cloudwatch_metric_alarm" "web_5xx" {
  count = local.web_enabled ? 1 : 0

  alarm_name          = "${local.name_prefix}-alb-5xx"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Sum"
  threshold           = 5
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = aws_lb.web[0].arn_suffix
    TargetGroup  = aws_lb_target_group.web[0].arn_suffix
  }
}

resource "aws_cloudwatch_dashboard" "web" {
  count = local.web_enabled ? 1 : 0

  dashboard_name = "${local.name_prefix}-web"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          title  = "ALB requests"
          region = var.aws_region
          metrics = [
            ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", aws_lb.web[0].arn_suffix],
          ]
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          title  = "Target 5xx"
          region = var.aws_region
          metrics = [
            [
              "AWS/ApplicationELB",
              "HTTPCode_Target_5XX_Count",
              "LoadBalancer",
              aws_lb.web[0].arn_suffix,
            ],
          ]
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          title   = "Daily spend GBP"
          region  = var.aws_region
          metrics = [["RagPlatform", "DailySpendGBP"]]
        }
      },
    ]
  })
}