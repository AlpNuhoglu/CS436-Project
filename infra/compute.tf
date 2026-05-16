# ── CloudWatch Log Group for ECS API ──────────────────────────────────────────
resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${var.project}-api"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "xray" {
  name              = "/ecs/${var.project}-xray"
  retention_in_days = 30
}

# ── IAM: ECS Task Execution Role ──────────────────────────────────────────────
resource "aws_iam_role" "ecs_task_execution" {
  name = "ecsTaskExecutionRole-${var.project}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_managed" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Allow task execution role to pull secrets from Secrets Manager
resource "aws_iam_role_policy" "ecs_task_execution_secrets" {
  name = "${var.project}-ecs-execution-secrets"
  role = aws_iam_role.ecs_task_execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["secretsmanager:GetSecretValue"]
        Resource = [
          "arn:aws:secretsmanager:eu-central-1:${data.aws_caller_identity.current.account_id}:secret:dersforumu/*"
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = [aws_kms_key.main.arn]
      },
      {
        Effect = "Allow"
        Action = ["ssm:GetParameters", "ssm:GetParameter"]
        Resource = [
          "arn:aws:ssm:eu-central-1:${data.aws_caller_identity.current.account_id}:parameter/dersforumu/*"
        ]
      }
    ]
  })
}

# ── IAM: ECS Task Role (runtime permissions) ───────────────────────────────────
resource "aws_iam_role" "ecs_task" {
  name = "ecsTaskRole-${var.project}-api"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# X-Ray write access
resource "aws_iam_role_policy_attachment" "ecs_task_xray" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

# SES send email (OTP)
resource "aws_iam_role_policy_attachment" "ecs_task_ses" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = aws_iam_policy.ses_send.arn
}

# ── Application Load Balancer ─────────────────────────────────────────────────
resource "aws_lb" "api" {
  name               = "${var.project}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection = false

  tags = { Name = "${var.project}-alb" }
}

resource "aws_lb_target_group" "api" {
  name        = "${var.project}-api-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    path                = "/api/health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    matcher             = "200"
  }

  tags = { Name = "${var.project}-api-tg" }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.api.arn
  port              = 80
  protocol          = "HTTP"

  # Forward all traffic to the API target group.
  # CloudFront sits in front and handles HTTPS termination.
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

# ── ECS Cluster ───────────────────────────────────────────────────────────────
resource "aws_ecs_cluster" "main" {
  name = var.project

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = { Name = var.project }
}

resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name       = aws_ecs_cluster.main.name
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
    base              = 1
  }
}

# ── ECS Task Definition ───────────────────────────────────────────────────────
resource "aws_ecs_task_definition" "api" {
  family                   = "${var.project}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 1024
  memory                   = 2048
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    # ── API container ──────────────────────────────────────────────────────
    {
      name      = "api"
      image     = "${aws_ecr_repository.api.repository_url}:latest"
      essential = true

      portMappings = [{
        containerPort = 8000
        protocol      = "tcp"
      }]

      environment = [
        { name = "COGNITO_REGION",      value = "eu-central-1" },
        { name = "COGNITO_USER_POOL_ID", value = aws_cognito_user_pool.main.id },
        { name = "COGNITO_APP_CLIENT_ID", value = aws_cognito_user_pool_client.api.id },
        { name = "ALLOWED_EMAIL_DOMAIN", value = "sabanciuniv.edu" },
        { name = "SMTP_FROM",            value = var.alert_email },
        { name = "AWS_XRAY_DAEMON_ADDRESS", value = "127.0.0.1:2000" },
      ]

      secrets = [
        # DB credentials — writer_url and reader_url keys from the secret JSON
        { name = "DATABASE_URL",        valueFrom = "${aws_secretsmanager_secret.db_master.arn}:writer_url::" },
        { name = "DATABASE_URL_READER", valueFrom = "${aws_secretsmanager_secret.db_master.arn}:reader_url::" },
        # JWT signing secret
        { name = "JWT_SECRET", valueFrom = "${aws_secretsmanager_secret.jwt.arn}:value::" },
        # Redis auth token → build the rediss:// URL in the app using REDIS_HOST + REDIS_AUTH_TOKEN
        { name = "REDIS_AUTH_TOKEN", valueFrom = "${aws_secretsmanager_secret.redis_auth.arn}:value::" },
        # SES SMTP credentials
        { name = "SMTP_USER",     valueFrom = "${aws_secretsmanager_secret.ses.arn}:smtp_user::" },
        { name = "SMTP_PASSWORD", valueFrom = "${aws_secretsmanager_secret.ses.arn}:smtp_password::" },
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.api.name
          "awslogs-region"        = "eu-central-1"
          "awslogs-stream-prefix" = "api"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/api/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    },

    # ── X-Ray daemon sidecar ───────────────────────────────────────────────
    {
      name      = "xray-daemon"
      image     = "public.ecr.aws/xray/aws-xray-daemon:latest"
      essential = false

      portMappings = [{
        containerPort = 2000
        protocol      = "udp"
      }]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.xray.name
          "awslogs-region"        = "eu-central-1"
          "awslogs-stream-prefix" = "xray"
        }
      }
    }
  ])

  tags = { Name = "${var.project}-api" }
}

# ── ECS Service ───────────────────────────────────────────────────────────────
resource "aws_ecs_service" "api" {
  name            = "${var.project}-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.app[*].id
    security_groups  = [aws_security_group.api.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  depends_on = [aws_lb_listener.http]

  tags = { Name = "${var.project}-api" }
}

# ── Auto Scaling ──────────────────────────────────────────────────────────────
resource "aws_appautoscaling_target" "api" {
  max_capacity       = 6
  min_capacity       = 2
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.api.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "api_cpu" {
  name               = "${var.project}-api-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.api.resource_id
  scalable_dimension = aws_appautoscaling_target.api.scalable_dimension
  service_namespace  = aws_appautoscaling_target.api.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value       = 60.0
    scale_in_cooldown  = 300
    scale_out_cooldown = 60

    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
  }
}

# ── Outputs ───────────────────────────────────────────────────────────────────
output "alb_dns_name"       { value = aws_lb.api.dns_name }
output "ecs_cluster_name"   { value = aws_ecs_cluster.main.name }
output "ecs_service_name"   { value = aws_ecs_service.api.name }
output "api_task_exec_role" { value = aws_iam_role.ecs_task_execution.arn }
output "api_task_role"      { value = aws_iam_role.ecs_task.arn }
