# ── CloudWatch Log Group for scraper ──────────────────────────────────────────
resource "aws_cloudwatch_log_group" "scraper" {
  name              = "/ecs/${var.project}-scraper"
  retention_in_days = 30
}

# ── IAM: Scraper Task Role ────────────────────────────────────────────────────
resource "aws_iam_role" "ecs_scraper_task" {
  name = "ecsTaskRole-${var.project}-scraper"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "scraper_task_xray" {
  role       = aws_iam_role.ecs_scraper_task.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

# ── ECS Task Definition: scraper ──────────────────────────────────────────────
resource "aws_ecs_task_definition" "scraper" {
  family                   = "${var.project}-scraper"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_scraper_task.arn

  container_definitions = jsonencode([
    {
      name      = "scraper"
      image     = "${aws_ecr_repository.scraper.repository_url}:latest"
      essential = true

      environment = []

      secrets = [
        { name = "DATABASE_URL",        valueFrom = "${aws_secretsmanager_secret.db_master.arn}:writer_url::" },
        { name = "DATABASE_URL_READER", valueFrom = "${aws_secretsmanager_secret.db_master.arn}:reader_url::" },
        { name = "SUIS_USERNAME",       valueFrom = "${aws_secretsmanager_secret.suis.arn}:username::" },
        { name = "SUIS_PASSWORD",       valueFrom = "${aws_secretsmanager_secret.suis.arn}:password::" },
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.scraper.name
          "awslogs-region"        = "eu-central-1"
          "awslogs-stream-prefix" = "scraper"
        }
      }
    }
  ])

  tags = { Name = "${var.project}-scraper" }
}

# ── IAM: Allow EventBridge Scheduler to run ECS tasks ────────────────────────
resource "aws_iam_role" "eventbridge_scheduler" {
  name = "${var.project}-eventbridge-scheduler"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "scheduler.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "eventbridge_scheduler" {
  name = "${var.project}-eventbridge-scheduler-policy"
  role = aws_iam_role.eventbridge_scheduler.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["ecs:RunTask"]
        Resource = [
          aws_ecs_task_definition.scraper.arn,
          # Allow running any revision of this task family
          "arn:aws:ecs:eu-central-1:${data.aws_caller_identity.current.account_id}:task-definition/${var.project}-scraper:*"
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = [
          aws_iam_role.ecs_task_execution.arn,
          aws_iam_role.ecs_scraper_task.arn,
        ]
      }
    ]
  })
}

# ── EventBridge Scheduler: run scraper every Sunday at 02:00 UTC ──────────────
resource "aws_scheduler_schedule" "scraper" {
  name                         = "${var.project}-scraper-weekly"
  description                  = "Run SUIS scraper every Sunday at 02:00 UTC"
  schedule_expression          = "cron(0 2 ? * SUN *)"
  schedule_expression_timezone = "UTC"
  state                        = "ENABLED"

  # Allow up to 15 minutes late if the scheduler misses the window
  flexible_time_window {
    mode                      = "FLEXIBLE"
    maximum_window_in_minutes = 15
  }

  target {
    arn      = aws_ecs_cluster.main.arn
    role_arn = aws_iam_role.eventbridge_scheduler.arn

    ecs_parameters {
      task_definition_arn = aws_ecs_task_definition.scraper.arn
      launch_type         = "FARGATE"
      task_count          = 1

      network_configuration {
        subnets          = aws_subnet.app[*].id
        security_groups  = [aws_security_group.api.id]
        assign_public_ip = false
      }
    }

    retry_policy {
      maximum_retry_attempts       = 2
      maximum_event_age_in_seconds = 3600
    }
  }
}

# ── CloudWatch Alarm: scraper task failed (exited non-zero) ───────────────────
resource "aws_cloudwatch_metric_alarm" "scraper_failed" {
  alarm_name          = "${var.project}-scraper-task-failed"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "FailedTaskCount"
  namespace           = "ECS/ContainerInsights"
  period              = 3600
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "SUIS scraper ECS task exited with non-zero code"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = "${var.project}-scraper"
  }

  tags = { Name = "${var.project}-scraper-failed" }
}

# ── Outputs ───────────────────────────────────────────────────────────────────
output "scraper_task_definition_arn" { value = aws_ecs_task_definition.scraper.arn }
output "scraper_schedule_arn"        { value = aws_scheduler_schedule.scraper.arn }
