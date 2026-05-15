# ── VPC ────────────────────────────────────────────────────────────────────────
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = { Name = "${var.project}-vpc" }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${var.project}-igw" }
}

# ── Subnets ────────────────────────────────────────────────────────────────────
locals {
  public_cidrs = ["10.20.0.0/24", "10.20.1.0/24", "10.20.2.0/24"]
  app_cidrs    = ["10.20.10.0/24", "10.20.11.0/24", "10.20.12.0/24"]
  data_cidrs   = ["10.20.20.0/24", "10.20.21.0/24", "10.20.22.0/24"]
}

resource "aws_subnet" "public" {
  count                   = 3
  vpc_id                  = aws_vpc.main.id
  cidr_block              = local.public_cidrs[count.index]
  availability_zone       = var.azs[count.index]
  map_public_ip_on_launch = true
  tags = { Name = "${var.project}-public-${count.index + 1}" }
}

resource "aws_subnet" "app" {
  count             = 3
  vpc_id            = aws_vpc.main.id
  cidr_block        = local.app_cidrs[count.index]
  availability_zone = var.azs[count.index]
  tags = { Name = "${var.project}-app-${count.index + 1}" }
}

resource "aws_subnet" "data" {
  count             = 3
  vpc_id            = aws_vpc.main.id
  cidr_block        = local.data_cidrs[count.index]
  availability_zone = var.azs[count.index]
  tags = { Name = "${var.project}-data-${count.index + 1}" }
}

# ── NAT Gateways (2 for cost/HA balance) ──────────────────────────────────────
resource "aws_eip" "nat" {
  count  = var.nat_gateway_count
  domain = "vpc"
  tags   = { Name = "${var.project}-nat-eip-${count.index + 1}" }
}

resource "aws_nat_gateway" "main" {
  count         = var.nat_gateway_count
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id
  tags          = { Name = "${var.project}-natgw-${count.index + 1}" }
  depends_on    = [aws_internet_gateway.igw]
}

# ── Route Tables ───────────────────────────────────────────────────────────────
# Public
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
  tags = { Name = "${var.project}-rt-public" }
}

resource "aws_route_table_association" "public" {
  count          = 3
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Private app — AZ-0 and AZ-1 each use their own NAT; AZ-2 falls back to NAT-1 (2-NAT trade-off)
resource "aws_route_table" "app" {
  count  = 3
  vpc_id = aws_vpc.main.id
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[min(count.index, var.nat_gateway_count - 1)].id
  }
  tags = { Name = "${var.project}-rt-app-${count.index + 1}" }
}

resource "aws_route_table_association" "app" {
  count          = 3
  subnet_id      = aws_subnet.app[count.index].id
  route_table_id = aws_route_table.app[count.index].id
}

# Data — local-only (no internet egress)
resource "aws_route_table" "data" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${var.project}-rt-data" }
}

resource "aws_route_table_association" "data" {
  count          = 3
  subnet_id      = aws_subnet.data[count.index].id
  route_table_id = aws_route_table.data.id
}

# ── VPC Endpoints ──────────────────────────────────────────────────────────────
# S3 Gateway endpoint (free, no ENI)
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.eu-central-1.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = concat(
    [aws_route_table.public.id],
    aws_route_table.app[*].id,
    [aws_route_table.data.id]
  )
  tags = { Name = "${var.project}-vpce-s3" }
}

# Interface endpoints — all in app subnets, using sg-endpoints
resource "aws_vpc_endpoint" "endpoints" {
  for_each = {
    ecr_api        = "com.amazonaws.eu-central-1.ecr.api"
    ecr_dkr        = "com.amazonaws.eu-central-1.ecr.dkr"
    logs           = "com.amazonaws.eu-central-1.logs"
    secretsmanager = "com.amazonaws.eu-central-1.secretsmanager"
    ssm            = "com.amazonaws.eu-central-1.ssm"
    ssmmessages    = "com.amazonaws.eu-central-1.ssmmessages"
    ec2messages    = "com.amazonaws.eu-central-1.ec2messages"
    monitoring     = "com.amazonaws.eu-central-1.monitoring"
  }
  vpc_id              = aws_vpc.main.id
  service_name        = each.value
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.app[*].id
  security_group_ids  = [aws_security_group.endpoints.id]
  private_dns_enabled = true
  tags = { Name = "${var.project}-vpce-${each.key}" }
}

# ── Security Groups ─────────────────────────────────────────────────────────────

# sg-alb: public ALB
resource "aws_security_group" "alb" {
  name        = "${var.project}-sg-alb"
  description = "ALB: 80 + 443 from internet"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTPS from internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    description = "HTTP from internet (redirect to HTTPS)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    description = "To ECS API tasks on 8000"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = local.app_cidrs
  }
  tags = { Name = "${var.project}-sg-alb" }
}

# sg-api: ECS Fargate tasks (API + scraper)
resource "aws_security_group" "api" {
  name        = "${var.project}-sg-api"
  description = "ECS tasks: inbound from ALB only, outbound to DB/Redis/AWS"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "From ALB on app port"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  # Outbound: HTTPS to AWS APIs (via VPC endpoints) and internet (SES, SUIS, Cognito)
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  # Outbound: PostgreSQL to Aurora
  egress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = local.data_cidrs
  }
  # Outbound: Redis to ElastiCache
  egress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = local.data_cidrs
  }
  tags = { Name = "${var.project}-sg-api" }
}

# sg-db: Aurora PostgreSQL
resource "aws_security_group" "db" {
  name        = "${var.project}-sg-db"
  description = "Aurora: inbound 5432 from ECS API only"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "PostgreSQL from ECS tasks"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.api.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
  }
  tags = { Name = "${var.project}-sg-db" }
}

# sg-redis: ElastiCache Redis
resource "aws_security_group" "redis" {
  name        = "${var.project}-sg-redis"
  description = "Redis: inbound 6379 from ECS tasks only"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Redis from ECS tasks"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.api.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
  }
  tags = { Name = "${var.project}-sg-redis" }
}

# sg-endpoints: VPC Interface Endpoints
resource "aws_security_group" "endpoints" {
  name        = "${var.project}-sg-endpoints"
  description = "VPC endpoints: inbound 443 from app tier"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTPS from ECS tasks"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = local.app_cidrs
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
  }
  tags = { Name = "${var.project}-sg-endpoints" }
}

# ── Network ACLs ───────────────────────────────────────────────────────────────
# ── Network ACL rules (separate resources for provider v5 compatibility) ───────

resource "aws_network_acl" "public" {
  vpc_id     = aws_vpc.main.id
  subnet_ids = aws_subnet.public[*].id
  tags       = { Name = "${var.project}-nacl-public" }
}
resource "aws_network_acl_rule" "public_in_443" {
  network_acl_id = aws_network_acl.public.id
  rule_number    = 100
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
  from_port      = 443
  to_port        = 443
}
resource "aws_network_acl_rule" "public_in_80" {
  network_acl_id = aws_network_acl.public.id
  rule_number    = 110
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
  from_port      = 80
  to_port        = 80
}
resource "aws_network_acl_rule" "public_in_eph" {
  network_acl_id = aws_network_acl.public.id
  rule_number    = 120
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
  from_port      = 1024
  to_port        = 65535
}
resource "aws_network_acl_rule" "public_out_443" {
  network_acl_id = aws_network_acl.public.id
  rule_number    = 100
  egress         = true
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
  from_port      = 443
  to_port        = 443
}
resource "aws_network_acl_rule" "public_out_80" {
  network_acl_id = aws_network_acl.public.id
  rule_number    = 110
  egress         = true
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
  from_port      = 80
  to_port        = 80
}
resource "aws_network_acl_rule" "public_out_eph" {
  network_acl_id = aws_network_acl.public.id
  rule_number    = 120
  egress         = true
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
  from_port      = 1024
  to_port        = 65535
}

resource "aws_network_acl" "app" {
  vpc_id     = aws_vpc.main.id
  subnet_ids = aws_subnet.app[*].id
  tags       = { Name = "${var.project}-nacl-app" }
}
resource "aws_network_acl_rule" "app_in_8000" {
  network_acl_id = aws_network_acl.app.id
  rule_number    = 100
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.vpc_cidr
  from_port      = 8000
  to_port        = 8000
}
resource "aws_network_acl_rule" "app_in_eph_vpc" {
  network_acl_id = aws_network_acl.app.id
  rule_number    = 110
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.vpc_cidr
  from_port      = 1024
  to_port        = 65535
}
resource "aws_network_acl_rule" "app_in_eph_net" {
  network_acl_id = aws_network_acl.app.id
  rule_number    = 120
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
  from_port      = 1024
  to_port        = 65535
}
resource "aws_network_acl_rule" "app_out_5432" {
  network_acl_id = aws_network_acl.app.id
  rule_number    = 100
  egress         = true
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.vpc_cidr
  from_port      = 5432
  to_port        = 5432
}
resource "aws_network_acl_rule" "app_out_6379" {
  network_acl_id = aws_network_acl.app.id
  rule_number    = 110
  egress         = true
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.vpc_cidr
  from_port      = 6379
  to_port        = 6379
}
resource "aws_network_acl_rule" "app_out_443" {
  network_acl_id = aws_network_acl.app.id
  rule_number    = 120
  egress         = true
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
  from_port      = 443
  to_port        = 443
}
resource "aws_network_acl_rule" "app_out_eph" {
  network_acl_id = aws_network_acl.app.id
  rule_number    = 130
  egress         = true
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
  from_port      = 1024
  to_port        = 65535
}

resource "aws_network_acl" "data" {
  vpc_id     = aws_vpc.main.id
  subnet_ids = aws_subnet.data[*].id
  tags       = { Name = "${var.project}-nacl-data" }
}
resource "aws_network_acl_rule" "data_in_5432" {
  network_acl_id = aws_network_acl.data.id
  rule_number    = 100
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "10.20.10.0/22"
  from_port      = 5432
  to_port        = 5432
}
resource "aws_network_acl_rule" "data_in_6379" {
  network_acl_id = aws_network_acl.data.id
  rule_number    = 110
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "10.20.10.0/22"
  from_port      = 6379
  to_port        = 6379
}
resource "aws_network_acl_rule" "data_in_eph" {
  network_acl_id = aws_network_acl.data.id
  rule_number    = 120
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.vpc_cidr
  from_port      = 1024
  to_port        = 65535
}
resource "aws_network_acl_rule" "data_out_eph" {
  network_acl_id = aws_network_acl.data.id
  rule_number    = 100
  egress         = true
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.vpc_cidr
  from_port      = 1024
  to_port        = 65535
}

# ── Outputs ────────────────────────────────────────────────────────────────────
output "vpc_id"             { value = aws_vpc.main.id }
output "public_subnet_ids"  { value = aws_subnet.public[*].id }
output "app_subnet_ids"     { value = aws_subnet.app[*].id }
output "data_subnet_ids"    { value = aws_subnet.data[*].id }
output "sg_alb_id"          { value = aws_security_group.alb.id }
output "sg_api_id"          { value = aws_security_group.api.id }
output "sg_db_id"           { value = aws_security_group.db.id }
output "sg_redis_id"        { value = aws_security_group.redis.id }
