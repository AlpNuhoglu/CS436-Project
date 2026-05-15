# ── KMS Customer Master Key ────────────────────────────────────────────────────
resource "aws_kms_key" "main" {
  description             = "dersforumu CMK for Aurora, ElastiCache, Secrets Manager"
  deletion_window_in_days = 7
  enable_key_rotation     = true
}
resource "aws_kms_alias" "main" {
  name          = "alias/dersforumu"
  target_key_id = aws_kms_key.main.key_id
}

# ── Random passwords ───────────────────────────────────────────────────────────
resource "random_password" "db_master" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}
resource "random_password" "redis_auth" {
  length  = 32
  special = false
}

# ── DB Subnet Group ────────────────────────────────────────────────────────────
resource "aws_db_subnet_group" "main" {
  name       = "${var.project}-db-subnet-group"
  subnet_ids = aws_subnet.data[*].id
  tags       = { Name = "${var.project}-db-subnet-group" }
}

# ── RDS Parameter Group ────────────────────────────────────────────────────────
# NOTE: Architecture calls for Aurora PostgreSQL Multi-AZ. Free-tier AWS accounts
# block Aurora (FreeTierRestrictionError). Using RDS PostgreSQL db.t3.micro
# (free-tier eligible) for the demo. On a paid account, replace this block with
# the Aurora Serverless v2 cluster from the deployment plan (data.tf.aurora_reference).
resource "aws_db_parameter_group" "main" {
  name   = "${var.project}-pg17"
  family = "postgres17"

  parameter {
    name  = "log_min_duration_statement"
    value = "500"
  }
  parameter {
    name  = "log_connections"
    value = "1"
  }
}

# ── RDS PostgreSQL db.t3.micro (free-tier, single-AZ) ─────────────────────────
resource "aws_db_instance" "main" {
  identifier        = "${var.project}-postgres"
  engine            = "postgres"
  engine_version    = "17.5"
  instance_class    = "db.t3.micro"
  allocated_storage = 20
  storage_type      = "gp2"

  db_name  = "ders_forumu"
  username = "dersforumu_admin"
  password = random_password.db_master.result

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]
  availability_zone      = var.azs[0]
  parameter_group_name   = aws_db_parameter_group.main.name

  backup_retention_period  = 1
  backup_window            = "02:00-03:00"
  maintenance_window       = "sun:04:00-sun:05:00"
  skip_final_snapshot      = false
  final_snapshot_identifier = "${var.project}-postgres-final"

  storage_encrypted = true
  kms_key_id        = aws_kms_key.main.arn

  enabled_cloudwatch_logs_exports = ["postgresql"]

  performance_insights_enabled = true
  # performance_insights_kms_key_id not set on free tier (uses default key)

  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.rds_monitoring.arn

  deletion_protection = false
  tags = { Name = "${var.project}-postgres" }
}

# Enhanced Monitoring IAM role
resource "aws_iam_role" "rds_monitoring" {
  name = "${var.project}-rds-enhanced-monitoring"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "monitoring.rds.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}
resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# ── ElastiCache Subnet Group ───────────────────────────────────────────────────
resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.project}-redis-subnet-group"
  subnet_ids = aws_subnet.data[*].id
  tags       = { Name = "${var.project}-redis-subnet-group" }
}

# ── ElastiCache Redis (Multi-AZ, auth token) ──────────────────────────────────
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id = "${var.project}-redis"
  description          = "Dersforumu Redis: OTP, rate-limit, session cache"

  node_type            = "cache.t4g.small"
  num_cache_clusters   = 2
  automatic_failover_enabled = true
  multi_az_enabled           = true

  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]

  at_rest_encryption_enabled  = true
  transit_encryption_enabled  = true
  auth_token                  = random_password.redis_auth.result
  auth_token_update_strategy  = "ROTATE"

  engine_version       = "7.1"
  parameter_group_name = "default.redis7"

  snapshot_retention_limit = 3
  snapshot_window          = "03:00-04:00"

  tags = { Name = "${var.project}-redis" }
}

# ── Secrets Manager ────────────────────────────────────────────────────────────
resource "aws_secretsmanager_secret" "db_master" {
  name       = "dersforumu/db/master"
  kms_key_id = aws_kms_key.main.id
}

# NOTE: writer_url and reader_url are the canonical keys injected as env vars
# into ECS tasks. The rotation Lambda must rebuild these URLs after each rotation.
resource "aws_secretsmanager_secret_version" "db_master" {
  secret_id = aws_secretsmanager_secret.db_master.id
  # On free tier: single RDS instance — writer_url and reader_url both point to
  # the same endpoint. On Aurora (paid), reader_url would use reader_endpoint.
  secret_string = jsonencode({
    username   = aws_db_instance.main.username
    password   = random_password.db_master.result
    host       = aws_db_instance.main.address
    reader     = aws_db_instance.main.address
    port       = 5432
    dbname     = "ders_forumu"
    writer_url = "postgresql+psycopg2://${aws_db_instance.main.username}:${random_password.db_master.result}@${aws_db_instance.main.address}:5432/ders_forumu?sslmode=require"
    reader_url = "postgresql+psycopg2://${aws_db_instance.main.username}:${random_password.db_master.result}@${aws_db_instance.main.address}:5432/ders_forumu?sslmode=require"
  })
}

resource "aws_secretsmanager_secret" "jwt" {
  name       = "dersforumu/jwt/secret"
  kms_key_id = aws_kms_key.main.id
}
resource "aws_secretsmanager_secret_version" "jwt" {
  secret_id     = aws_secretsmanager_secret.jwt.id
  secret_string = jsonencode({ value = random_password.db_master.result })
}

resource "aws_secretsmanager_secret" "ses" {
  name       = "dersforumu/ses/smtp"
  kms_key_id = aws_kms_key.main.id
}
resource "aws_secretsmanager_secret_version" "ses" {
  secret_id     = aws_secretsmanager_secret.ses.id
  secret_string = jsonencode({ smtp_user = "", smtp_password = "" })
}

resource "aws_secretsmanager_secret" "cognito" {
  name       = "dersforumu/cognito/client"
  kms_key_id = aws_kms_key.main.id
}
resource "aws_secretsmanager_secret_version" "cognito" {
  secret_id     = aws_secretsmanager_secret.cognito.id
  secret_string = jsonencode({ client_secret = "" })
}

resource "aws_secretsmanager_secret" "redis_auth" {
  name       = "dersforumu/redis/authtoken"
  kms_key_id = aws_kms_key.main.id
}
resource "aws_secretsmanager_secret_version" "redis_auth" {
  secret_id     = aws_secretsmanager_secret.redis_auth.id
  secret_string = jsonencode({ value = random_password.redis_auth.result })
}

resource "aws_secretsmanager_secret" "suis" {
  name       = "dersforumu/suis/credentials"
  kms_key_id = aws_kms_key.main.id
}
resource "aws_secretsmanager_secret_version" "suis" {
  secret_id     = aws_secretsmanager_secret.suis.id
  secret_string = jsonencode({ username = "", password = "" })
}

# ── SSM Parameter Store ────────────────────────────────────────────────────────
resource "aws_ssm_parameter" "log_level" {
  name  = "/dersforumu/log_level"
  type  = "String"
  value = "INFO"
}
resource "aws_ssm_parameter" "cognito_region" {
  name  = "/dersforumu/cognito/region"
  type  = "String"
  value = "eu-central-1"
}
resource "aws_ssm_parameter" "cognito_user_pool_id" {
  name  = "/dersforumu/cognito/user_pool_id"
  type  = "String"
  value = "placeholder"
}
resource "aws_ssm_parameter" "cognito_client_id" {
  name  = "/dersforumu/cognito/client_id"
  type  = "String"
  value = "placeholder"
}

# ── Outputs ────────────────────────────────────────────────────────────────────
output "db_writer_endpoint"     { value = aws_db_instance.main.address }
output "db_reader_endpoint"     { value = aws_db_instance.main.address }
output "redis_primary_endpoint" { value = aws_elasticache_replication_group.redis.primary_endpoint_address }
output "kms_key_arn"            { value = aws_kms_key.main.arn }
output "db_secret_arn"          { value = aws_secretsmanager_secret.db_master.arn }
