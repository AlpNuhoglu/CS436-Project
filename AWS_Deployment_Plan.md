# Deployment Plan for Ders Forumu on AWS

## Table of Contents

- Phase 0 – Preparation & Bootstrap
- Phase 1 – Networking Foundation
- Phase 2 – Data Layer (Aurora + ElastiCache + Secrets)
- Phase 3 – Identity & Mail (Cognito + SES)
- Phase 4 – Container Registry & Builds (ECR + CI/CD)
- Phase 5 – Frontend Hosting (S3 + CloudFront)
- Phase 6 – Compute (ALB + ECS Fargate API)
- Phase 7 – Scheduled Scraper (EventBridge → ECS RunTask)
- Phase 8 – Monitoring & Alarms (CloudWatch + X-Ray + SNS)
- Phase 9 – Security Hardening (WAF + CloudTrail + GuardDuty + Config)
- Phase 10 – DNS Cutover & Go-Live
- Summary Checklist
- Post-Deployment Validation Script

## Critical Dependencies Table

| Phase | Depends on |
|---|---|
| 0 Bootstrap | — |
| 1 Networking | 0 |
| 2 Data Layer | 1 |
| 3 Identity & Mail | 0 (Route 53 domain) |
| 4 ECR & CI/CD | 0 |
| 5 Frontend (S3+CF) | 0 (ACM us-east-1), 3 (optional) |
| 6 Compute (ECS API) | 1, 2, 3, 4 |
| 7 Scraper | 1, 2, 4 |
| 8 Monitoring | 5, 6, 7 |
| 9 Security Hardening | 5, 6 (WAF attaches to CF; CloudTrail/GuardDuty/Config are account-wide) |
| 10 Cutover | All previous |

---

## Phase 0 – Preparation & Bootstrap

**Objective:** Establish the AWS account baseline (root MFA, admin IAM identities), local tooling (AWS CLI v2, Terraform), domain & TLS, Terraform remote-state backend, budget guardrails, and a GitHub Actions OIDC trust relationship so subsequent phases can be provisioned reproducibly and without long-lived AWS keys.

**Prerequisites:**
- An AWS account (root credentials, billing access).
- A GitHub repository for the project.
- A workstation with macOS/Linux shell, `git`, and admin rights to install tools.

**Steps:**

1. **Secure the root account.**
   - Sign in as root, enable virtual MFA, remove root access keys.
   - Set the account alias: `aws iam create-account-alias --account-alias dersforumu-prod`.

2. **Create the bootstrap admin IAM user.**
   ```bash
   aws iam create-group --group-name Admins
   aws iam attach-group-policy --group-name Admins \
     --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
   aws iam create-user --user-name alp-admin
   aws iam add-user-to-group --user-name alp-admin --group-name Admins
   aws iam create-login-profile --user-name alp-admin --password '<temp>' --password-reset-required
   aws iam enable-mfa-device --user-name alp-admin --serial-number <arn> --authentication-code1 ... --authentication-code2 ...
   aws iam create-access-key --user-name alp-admin     # store in ~/.aws/credentials profile dersforumu
   ```

3. **Install CLIs.**
   ```bash
   # AWS CLI v2 (macOS)
   curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o AWSCLIV2.pkg
   sudo installer -pkg AWSCLIV2.pkg -target /
   aws configure --profile dersforumu       # region eu-central-1
   # Terraform via tfenv
   brew install tfenv && tfenv install 1.9.5 && tfenv use 1.9.5
   # gitleaks
   brew install gitleaks
   ```

4. **Register the domain in Route 53.**
   - Console → Route 53 → Registered domains → Register `dersforumu.com` (~$12/yr for `.com`).
   - The public hosted zone is auto-created. Note the zone ID.

5. **Request ACM certificates (two regions, DNS-validated).**
   ```bash
   # For CloudFront (must be us-east-1)
   aws acm request-certificate --region us-east-1 \
     --domain-name dersforumu.com \
     --subject-alternative-names www.dersforumu.com \
     --validation-method DNS

   # For ALB (eu-central-1)
   aws acm request-certificate --region eu-central-1 \
     --domain-name api.dersforumu.com \
     --validation-method DNS
   ```
   For each returned cert ARN, run `aws acm describe-certificate ...` to get the CNAME validation records and create them in Route 53 (`aws route53 change-resource-record-sets ...`).

6. **Terraform remote state bootstrap** (run once with local state, then migrate).
   ```bash
   aws s3api create-bucket --bucket dersforumu-tfstate \
     --region eu-central-1 \
     --create-bucket-configuration LocationConstraint=eu-central-1
   aws s3api put-bucket-versioning --bucket dersforumu-tfstate \
     --versioning-configuration Status=Enabled
   aws s3api put-bucket-encryption --bucket dersforumu-tfstate \
     --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
   aws s3api put-public-access-block --bucket dersforumu-tfstate \
     --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
   aws dynamodb create-table --table-name dersforumu-tflock \
     --attribute-definitions AttributeName=LockID,AttributeType=S \
     --key-schema AttributeName=LockID,KeyType=HASH \
     --billing-mode PAY_PER_REQUEST --region eu-central-1
   ```

7. **Terraform root module skeleton.** Create `infra/` in the repo:

   `infra/versions.tf`
   ```hcl
   terraform {
     required_version = ">= 1.9.0"
     required_providers {
       aws = { source = "hashicorp/aws", version = "~> 5.60" }
     }
     backend "s3" {
       bucket         = "dersforumu-tfstate"
       key            = "prod/terraform.tfstate"
       region         = "eu-central-1"
       dynamodb_table = "dersforumu-tflock"
       encrypt        = true
     }
   }

   provider "aws" {
     region = "eu-central-1"
     default_tags { tags = { Project = "dersforumu", Env = "prod", ManagedBy = "terraform" } }
   }
   provider "aws" {
     alias  = "us_east_1"
     region = "us-east-1"
     default_tags { tags = { Project = "dersforumu", Env = "prod", ManagedBy = "terraform" } }
   }
   ```

   `infra/variables.tf`
   ```hcl
   variable "project"       { default = "dersforumu" }
   variable "env"           { default = "prod" }
   variable "vpc_cidr"      { default = "10.20.0.0/16" }
   variable "azs"           { default = ["eu-central-1a","eu-central-1b","eu-central-1c"] }
   variable "domain_name"   { default = "dersforumu.com" }
   variable "api_subdomain" { default = "api.dersforumu.com" }
   variable "acm_cf_arn"    {}  # us-east-1 cert
   variable "acm_alb_arn"   {}  # eu-central-1 cert
   variable "hosted_zone_id"{}
   ```

8. **Budgets alert.**
   ```bash
   aws budgets create-budget --account-id $(aws sts get-caller-identity --query Account --output text) \
     --budget '{"BudgetName":"dersforumu-monthly","BudgetLimit":{"Amount":"400","Unit":"USD"},"TimeUnit":"MONTHLY","BudgetType":"COST"}' \
     --notifications-with-subscribers '[{"Notification":{"NotificationType":"ACTUAL","ComparisonOperator":"GREATER_THAN","Threshold":80},"Subscribers":[{"SubscriptionType":"EMAIL","Address":"alpnuhoglu2@gmail.com"}]}]'
   ```

9. **Pre-commit secret scanning.**
   ```bash
   pip install pre-commit
   cat > .pre-commit-config.yaml <<'EOF'
   repos:
     - repo: https://github.com/gitleaks/gitleaks
       rev: v8.18.4
       hooks: [{id: gitleaks}]
   EOF
   pre-commit install
   ```

10. **GitHub Actions OIDC federation.**
    ```hcl
    resource "aws_iam_openid_connect_provider" "github" {
      url             = "https://token.actions.githubusercontent.com"
      client_id_list  = ["sts.amazonaws.com"]
      thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
    }

    data "aws_iam_policy_document" "gh_trust" {
      statement {
        actions = ["sts:AssumeRoleWithWebIdentity"]
        principals { type = "Federated" identifiers = [aws_iam_openid_connect_provider.github.arn] }
        condition { test="StringEquals" variable="token.actions.githubusercontent.com:aud" values=["sts.amazonaws.com"] }
        condition { test="StringLike"   variable="token.actions.githubusercontent.com:sub" values=["repo:AlpNuhoglu/CS436-Project:*"] }
      }
    }

    resource "aws_iam_role" "github_deployer" {
      name               = "gha-dersforumu-deployer"
      assume_role_policy = data.aws_iam_policy_document.gh_trust.json
    }

    # Attach least-privilege deploy policy (ECR push, ECS update-service, S3 sync, CloudFront invalidation)
    ```

**Verification:**
- `aws sts get-caller-identity` returns the admin user.
- `aws acm list-certificates --region us-east-1` shows ISSUED cert for dersforumu.com.
- `aws s3 ls s3://dersforumu-tfstate` succeeds.
- `terraform init` in `infra/` connects to the S3 backend.
- A test GitHub Action assuming `gha-dersforumu-deployer` shows `aws sts get-caller-identity` succeeds.

---

## Phase 1 – Networking Foundation

**Objective:** Build a 3-AZ VPC at `10.20.0.0/16` with public, app, and data tiers; egress via NAT GWs; private AWS-service traffic via interface/gateway endpoints; tier-scoped security groups. This is the security perimeter on which everything else lands.

**Prerequisites:** Phase 0 (Terraform backend, profile).

**Trade-off — NAT Gateways:**
- 3 NAT GWs (one per AZ): ~$100/mo, fully AZ-independent (recommended for true prod).
- 2 NAT GWs: ~$66/mo, one AZ pinned to another's NAT — acceptable for a university project.
- 1 NAT GW: ~$33/mo, single point of failure. **Default in this plan: 2 NAT GWs** for a cost/HA balance; flip `var.nat_gateway_count` to 3 for the architecture document spec.

**Steps:**

1. **Add networking module variables** to `infra/variables.tf`:
   ```hcl
   variable "nat_gateway_count" { default = 2 }
   ```

2. **`infra/network.tf`** (complete HCL):
   ```hcl
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

   locals {
     public_cidrs = ["10.20.0.0/24","10.20.1.0/24","10.20.2.0/24"]
     app_cidrs    = ["10.20.10.0/24","10.20.11.0/24","10.20.12.0/24"]
     data_cidrs   = ["10.20.20.0/24","10.20.21.0/24","10.20.22.0/24"]
   }

   resource "aws_subnet" "public" {
     count                   = 3
     vpc_id                  = aws_vpc.main.id
     cidr_block              = local.public_cidrs[count.index]
     availability_zone       = var.azs[count.index]
     map_public_ip_on_launch = true
     tags = { Name = "${var.project}-public-${var.azs[count.index]}", Tier="public" }
   }
   resource "aws_subnet" "app" {
     count             = 3
     vpc_id            = aws_vpc.main.id
     cidr_block        = local.app_cidrs[count.index]
     availability_zone = var.azs[count.index]
     tags = { Name = "${var.project}-app-${var.azs[count.index]}", Tier="app" }
   }
   resource "aws_subnet" "data" {
     count             = 3
     vpc_id            = aws_vpc.main.id
     cidr_block        = local.data_cidrs[count.index]
     availability_zone = var.azs[count.index]
     tags = { Name = "${var.project}-data-${var.azs[count.index]}", Tier="data" }
   }

   # NAT
   resource "aws_eip" "nat" {
     count  = var.nat_gateway_count
     domain = "vpc"
     tags   = { Name = "${var.project}-nat-eip-${count.index}" }
   }
   resource "aws_nat_gateway" "nat" {
     count         = var.nat_gateway_count
     allocation_id = aws_eip.nat[count.index].id
     subnet_id     = aws_subnet.public[count.index].id
     tags          = { Name = "${var.project}-nat-${count.index}" }
   }

   # Route tables
   resource "aws_route_table" "public" {
     vpc_id = aws_vpc.main.id
     route { cidr_block = "0.0.0.0/0" gateway_id = aws_internet_gateway.igw.id }
     tags = { Name = "${var.project}-rt-public" }
   }
   resource "aws_route_table_association" "public" {
     count          = 3
     subnet_id      = aws_subnet.public[count.index].id
     route_table_id = aws_route_table.public.id
   }

   resource "aws_route_table" "private" {
     count  = 3
     vpc_id = aws_vpc.main.id
     route {
       cidr_block     = "0.0.0.0/0"
       nat_gateway_id = aws_nat_gateway.nat[count.index % var.nat_gateway_count].id
     }
     tags = { Name = "${var.project}-rt-private-${count.index}" }
   }
   resource "aws_route_table_association" "app" {
     count          = 3
     subnet_id      = aws_subnet.app[count.index].id
     route_table_id = aws_route_table.private[count.index].id
   }
   resource "aws_route_table_association" "data" {
     count          = 3
     subnet_id      = aws_subnet.data[count.index].id
     route_table_id = aws_route_table.private[count.index].id
   }
   ```

3. **Security Groups** (`infra/sg.tf`):
   ```hcl
   resource "aws_security_group" "alb" {
     name = "sg-alb" vpc_id = aws_vpc.main.id
     ingress { from_port=443 to_port=443 protocol="tcp" cidr_blocks=["0.0.0.0/0"] }
     ingress { from_port=80  to_port=80  protocol="tcp" cidr_blocks=["0.0.0.0/0"] }
     egress  { from_port=0   to_port=0   protocol="-1" cidr_blocks=["0.0.0.0/0"] }
   }
   resource "aws_security_group" "api" {
     name = "sg-api" vpc_id = aws_vpc.main.id
     ingress { from_port=8000 to_port=8000 protocol="tcp" security_groups=[aws_security_group.alb.id] }
     egress  { from_port=0    to_port=0    protocol="-1" cidr_blocks=["0.0.0.0/0"] }
   }
   resource "aws_security_group" "db" {
     name = "sg-db" vpc_id = aws_vpc.main.id
     ingress { from_port=5432 to_port=5432 protocol="tcp" security_groups=[aws_security_group.api.id] }
   }
   resource "aws_security_group" "redis" {
     name = "sg-redis" vpc_id = aws_vpc.main.id
     ingress { from_port=6379 to_port=6379 protocol="tcp" security_groups=[aws_security_group.api.id] }
   }
   resource "aws_security_group" "endpoints" {
     name = "sg-endpoints" vpc_id = aws_vpc.main.id
     ingress { from_port=443 to_port=443 protocol="tcp" security_groups=[aws_security_group.api.id] }
   }
   ```

4. **VPC Endpoints** (`infra/endpoints.tf`):
   ```hcl
   resource "aws_vpc_endpoint" "s3" {
     vpc_id            = aws_vpc.main.id
     service_name      = "com.amazonaws.eu-central-1.s3"
     vpc_endpoint_type = "Gateway"
     route_table_ids   = aws_route_table.private[*].id
   }

   locals {
     interface_services = [
       "ecr.api","ecr.dkr","logs","secretsmanager","ssm","ssmmessages","ec2messages","monitoring"
     ]
   }
   resource "aws_vpc_endpoint" "interface" {
     for_each            = toset(local.interface_services)
     vpc_id              = aws_vpc.main.id
     service_name        = "com.amazonaws.eu-central-1.${each.key}"
     vpc_endpoint_type   = "Interface"
     subnet_ids          = aws_subnet.app[*].id
     security_group_ids  = [aws_security_group.endpoints.id]
     private_dns_enabled = true
   }
   ```

5. **Network ACLs.** Add stateless allow-only for tier ports (443 ingress on public-tier NACL, ephemeral 1024-65535 return, 5432/6379 only between app/data tiers). Default VPC NACL is allow-all; explicit NACLs add defense-in-depth.

6. `terraform apply -target=module.network` (or just `terraform apply` if single-module).

**Verification:**
- `aws ec2 describe-vpcs --filters Name=tag:Name,Values=dersforumu-vpc` returns the VPC.
- `aws ec2 describe-nat-gateways --filter Name=state,Values=available` returns 2 (or 3).
- `aws ec2 describe-vpc-endpoints` lists 9 endpoints (1 gateway + 8 interface).
- From a temporary SSM-enabled instance in the app subnet: `curl https://secretsmanager.eu-central-1.amazonaws.com` resolves to a private IP (10.20.x.x).

---

## Phase 2 – Data Layer (Aurora + ElastiCache + Secrets)

**Objective:** Provision the encrypted, Multi-AZ stateful tier — Aurora PostgreSQL cluster (writer + reader), ElastiCache Redis (primary + replica), DB/cache subnet groups, parameter groups enforcing TLS, the KMS CMK, and all six Secrets Manager entries (with rotation on the master DB secret).

**Prerequisites:** Phase 1.

**Trade-off — Aurora Serverless v2 (0.5–4 ACU)** is ~50–70% cheaper at low load and auto-scales, but cold-start ramp is ~15 s. For a CS436 demo budget, Serverless v2 is recommended; for the architecture-doc spec, provisioned `db.r6g.large` writer+reader is shown below. Toggle via `var.aurora_serverless`.

**Steps:**

1. **KMS CMK** (`infra/kms.tf`):
   ```hcl
   resource "aws_kms_key" "main" {
     description             = "kms/dersforumu"
     enable_key_rotation     = true
     deletion_window_in_days = 30
   }
   resource "aws_kms_alias" "main" {
     name          = "alias/dersforumu"
     target_key_id = aws_kms_key.main.id
   }
   ```

2. **Aurora cluster** (`infra/aurora.tf`):
   ```hcl
   resource "aws_db_subnet_group" "aurora" {
     name       = "${var.project}-aurora-subnets"
     subnet_ids = aws_subnet.data[*].id
   }

   resource "aws_rds_cluster_parameter_group" "aurora" {
     name   = "${var.project}-aurora-pg"
     family = "aurora-postgresql16"
     parameter { name="rds.force_ssl" value="1" apply_method="pending-reboot" }
   }

   resource "random_password" "db_master" { length=24 special=true override_special="!#$%&*()-_=+" }

   resource "aws_rds_cluster" "main" {
     cluster_identifier              = "${var.project}-aurora"
     engine                          = "aurora-postgresql"
     engine_version                  = "16.4"
     database_name                   = "dersforumu"
     master_username                 = "dersforumu_admin"
     master_password                 = random_password.db_master.result
     db_subnet_group_name            = aws_db_subnet_group.aurora.name
     vpc_security_group_ids          = [aws_security_group.db.id]
     kms_key_id                      = aws_kms_key.main.arn
     storage_encrypted               = true
     backup_retention_period         = 14
     preferred_backup_window         = "02:00-03:00"
     db_cluster_parameter_group_name = aws_rds_cluster_parameter_group.aurora.name
     deletion_protection             = true
     enabled_cloudwatch_logs_exports = ["postgresql"]
     skip_final_snapshot             = false
     final_snapshot_identifier       = "${var.project}-aurora-final"
   }

   resource "aws_rds_cluster_instance" "writer" {
     identifier              = "${var.project}-aurora-writer"
     cluster_identifier      = aws_rds_cluster.main.id
     instance_class          = "db.r6g.large"
     engine                  = aws_rds_cluster.main.engine
     engine_version          = aws_rds_cluster.main.engine_version
     availability_zone       = var.azs[0]
     performance_insights_enabled = true
     monitoring_interval     = 30
     monitoring_role_arn     = aws_iam_role.rds_monitoring.arn
   }
   resource "aws_rds_cluster_instance" "reader" {
     identifier              = "${var.project}-aurora-reader"
     cluster_identifier      = aws_rds_cluster.main.id
     instance_class          = "db.r6g.large"
     engine                  = aws_rds_cluster.main.engine
     engine_version          = aws_rds_cluster.main.engine_version
     availability_zone       = var.azs[1]
     performance_insights_enabled = true
     monitoring_interval     = 30
     monitoring_role_arn     = aws_iam_role.rds_monitoring.arn
   }

   resource "aws_iam_role" "rds_monitoring" {
     name = "${var.project}-rds-monitoring"
     assume_role_policy = jsonencode({
       Version="2012-10-17",
       Statement=[{Effect="Allow",Principal={Service="monitoring.rds.amazonaws.com"},Action="sts:AssumeRole"}]
     })
   }
   resource "aws_iam_role_policy_attachment" "rds_monitoring" {
     role       = aws_iam_role.rds_monitoring.name
     policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
   }
   ```

3. **ElastiCache Redis** (`infra/redis.tf`):
   ```hcl
   resource "aws_elasticache_subnet_group" "redis" {
     name       = "${var.project}-redis-subnets"
     subnet_ids = aws_subnet.data[*].id
   }
   resource "random_password" "redis_auth" { length=32 special=false }

   resource "aws_elasticache_replication_group" "redis" {
     replication_group_id        = "${var.project}-redis"
     description                 = "Dersforumu Redis"
     engine                      = "redis"
     engine_version              = "7.1"
     node_type                   = "cache.t4g.small"
     num_cache_clusters          = 2
     automatic_failover_enabled  = true
     multi_az_enabled            = true
     subnet_group_name           = aws_elasticache_subnet_group.redis.name
     security_group_ids          = [aws_security_group.redis.id]
     at_rest_encryption_enabled  = true
     transit_encryption_enabled  = true
     auth_token                  = random_password.redis_auth.result
     kms_key_id                  = aws_kms_key.main.arn
     snapshot_retention_limit    = 7
   }
   ```

4. **Secrets Manager** (`infra/secrets.tf`):
   ```hcl
   resource "aws_secretsmanager_secret" "db_master" {
     name       = "dersforumu/db/master"
     kms_key_id = aws_kms_key.main.id
   }
   # NOTE: writer_url and reader_url are the canonical keys referenced by the
   # ECS task definition secrets injection (Phase 6). They include the full
   # connection string so ECS can inject them directly as DATABASE_URL /
   # DATABASE_URL_READER without the app constructing URLs at runtime.
   resource "aws_secretsmanager_secret_version" "db_master" {
     secret_id = aws_secretsmanager_secret.db_master.id
     secret_string = jsonencode({
       username   = aws_rds_cluster.main.master_username
       password   = random_password.db_master.result
       host       = aws_rds_cluster.main.endpoint
       reader     = aws_rds_cluster.main.reader_endpoint
       port       = 5432
       dbname     = "dersforumu"
       writer_url = "postgresql+psycopg2://${aws_rds_cluster.main.master_username}:${random_password.db_master.result}@${aws_rds_cluster.main.endpoint}:5432/dersforumu?sslmode=require"
       reader_url = "postgresql+psycopg2://${aws_rds_cluster.main.master_username}:${random_password.db_master.result}@${aws_rds_cluster.main.reader_endpoint}:5432/dersforumu?sslmode=require"
     })
   }
   # IMPORTANT: When Secrets Manager rotates the DB password (every 30 days),
   # the rotation Lambda MUST also update writer_url and reader_url in the
   # secret JSON — not just `password`. Use a custom rotation Lambda (or extend
   # the AWS-provided template) that rebuilds the full URL strings after each
   # credential rotation. The ECS tasks will automatically pick up the new
   # secret on their next deployment or task restart.

   resource "aws_secretsmanager_secret" "jwt"          { name="dersforumu/jwt/secret"        kms_key_id=aws_kms_key.main.id }
   resource "aws_secretsmanager_secret" "ses"          { name="dersforumu/ses/smtp"          kms_key_id=aws_kms_key.main.id }
   resource "aws_secretsmanager_secret" "cognito"      { name="dersforumu/cognito/client"    kms_key_id=aws_kms_key.main.id }
   resource "aws_secretsmanager_secret" "redis_auth"   { name="dersforumu/redis/authtoken"   kms_key_id=aws_kms_key.main.id }
   resource "aws_secretsmanager_secret" "suis"         { name="dersforumu/suis/credentials"  kms_key_id=aws_kms_key.main.id }

   # 30-day rotation of DB master via Lambda from the AWS-provided template
   resource "aws_secretsmanager_secret_rotation" "db_master" {
     secret_id           = aws_secretsmanager_secret.db_master.id
     rotation_lambda_arn = aws_lambda_function.db_rotator.arn
     rotation_rules { automatically_after_days = 30 }
   }
   ```
   (`aws_lambda_function.db_rotator` uses the AWS Serverless Application Repository template `SecretsManagerRDSPostgreSQLRotationSingleUser` deployed into the app subnets with `sg-api`.)

5. **Parameter Store** non-secret config:
   ```bash
   aws ssm put-parameter --name /dersforumu/log_level   --value INFO --type String
   aws ssm put-parameter --name /dersforumu/feature_flags/enable_reviews --value true --type String
   ```

**Verification:**
- `aws rds describe-db-clusters --db-cluster-identifier dersforumu-aurora --query 'DBClusters[0].Status'` → `available`; `Endpoint` and `ReaderEndpoint` distinct.
- `aws elasticache describe-replication-groups --replication-group-id dersforumu-redis --query 'ReplicationGroups[0].Status'` → `available`; `AutomaticFailover=enabled`.
- `aws secretsmanager list-secrets --query 'SecretList[].Name'` shows all six secrets.

---

## Phase 3 – Identity & Mail (Cognito + SES)

**Objective:** Stand up the user identity store (Cognito) with a domain-restriction pre-sign-up Lambda and the transactional-email plane (SES) with DKIM/SPF/DMARC so the application can authenticate users and send OTP/notification emails.

**Prerequisites:** Phase 0 (Route 53 hosted zone).

**Steps:**

1. **Pre-sign-up Lambda** (`infra/lambda_presignup.tf`):
   ```hcl
   data "archive_file" "presignup" {
     type        = "zip"
     output_path = "${path.module}/build/presignup.zip"
     source { filename = "index.py" content = <<-EOT
       def handler(event, context):
           email = event["request"]["userAttributes"].get("email", "")
           if not email.lower().endswith("@sabanciuniv.edu"):
               raise Exception("Only @sabanciuniv.edu emails are allowed")
           event["response"]["autoConfirmUser"]  = False
           event["response"]["autoVerifyEmail"]  = False
           return event
     EOT
     }
   }
   resource "aws_iam_role" "presignup" {
     name = "${var.project}-cognito-presignup"
     assume_role_policy = jsonencode({Version="2012-10-17",Statement=[{Effect="Allow",Principal={Service="lambda.amazonaws.com"},Action="sts:AssumeRole"}]})
   }
   resource "aws_iam_role_policy_attachment" "presignup_basic" {
     role       = aws_iam_role.presignup.name
     policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
   }
   resource "aws_lambda_function" "presignup" {
     function_name    = "${var.project}-cognito-presignup"
     role             = aws_iam_role.presignup.arn
     runtime          = "python3.12"
     handler          = "index.handler"
     filename         = data.archive_file.presignup.output_path
     source_code_hash = data.archive_file.presignup.output_base64sha256
   }
   ```

2. **Cognito User Pool**:
   ```hcl
   resource "aws_cognito_user_pool" "main" {
     name = "${var.project}-users"
     username_attributes      = ["email"]
     auto_verified_attributes = ["email"]
     password_policy {
       minimum_length    = 10
       require_lowercase = true
       require_uppercase = true
       require_numbers   = true
       require_symbols   = true
     }
     mfa_configuration = "OPTIONAL"
     software_token_mfa_configuration { enabled = true }
     lambda_config { pre_sign_up = aws_lambda_function.presignup.arn }
     account_recovery_setting { recovery_mechanism { name="verified_email" priority=1 } }
   }
   resource "aws_lambda_permission" "cognito_invoke" {
     statement_id  = "AllowCognitoInvoke"
     action        = "lambda:InvokeFunction"
     function_name = aws_lambda_function.presignup.function_name
     principal     = "cognito-idp.amazonaws.com"
     source_arn    = aws_cognito_user_pool.main.arn
   }
   resource "aws_cognito_user_pool_client" "web" {
     name            = "web-spa"
     user_pool_id    = aws_cognito_user_pool.main.id
     generate_secret = false
     explicit_auth_flows = ["ALLOW_USER_SRP_AUTH","ALLOW_REFRESH_TOKEN_AUTH"]
     prevent_user_existence_errors = "ENABLED"
   }
   ```

3. **Store Cognito IDs in SSM Parameter Store**:
   ```bash
   aws ssm put-parameter --name /dersforumu/cognito/user_pool_id --value $POOL_ID --type String --overwrite
   aws ssm put-parameter --name /dersforumu/cognito/client_id    --value $CLIENT_ID --type String --overwrite
   aws ssm put-parameter --name /dersforumu/cognito/region       --value eu-central-1 --type String --overwrite
   ```

4. **SES domain identity + DKIM**:
   ```hcl
   resource "aws_sesv2_email_identity" "domain" {
     email_identity = var.domain_name
     dkim_signing_attributes { next_signing_key_length = "RSA_2048_BIT" }
   }
   resource "aws_route53_record" "dkim" {
     count   = 3
     zone_id = var.hosted_zone_id
     name    = "${aws_sesv2_email_identity.domain.dkim_signing_attributes[0].tokens[count.index]}._domainkey.${var.domain_name}"
     type    = "CNAME"
     ttl     = 600
     records = ["${aws_sesv2_email_identity.domain.dkim_signing_attributes[0].tokens[count.index]}.dkim.amazonses.com"]
   }
   resource "aws_route53_record" "spf" {
     zone_id = var.hosted_zone_id name = var.domain_name type = "TXT" ttl=600
     records = ["v=spf1 include:amazonses.com -all"]
   }
   resource "aws_route53_record" "dmarc" {
     zone_id = var.hosted_zone_id name = "_dmarc.${var.domain_name}" type = "TXT" ttl=600
     records = ["v=DMARC1; p=quarantine; rua=mailto:dmarc@dersforumu.com"]
   }
   resource "aws_sesv2_configuration_set" "main" {
     configuration_set_name = "${var.project}-cs"
     suppression_options    { suppressed_reasons = ["BOUNCE","COMPLAINT"] }
   }
   ```

5. **IAM role for ECS task to send via SES** — see Phase 6 `ecsTaskRole-dersforumu-api`.

6. **Production access:** open an SES quota increase ticket to leave sandbox (default 200 emails/day).

**Verification:**
- `aws sesv2 get-email-identity --email-identity dersforumu.com` → `VerifiedForSendingStatus: true`, `DkimAttributes.Status: SUCCESS`.
- Cognito console → sign-up with `test@gmail.com` → rejected. With `test@sabanciuniv.edu` → confirmation email sent.

---

## Phase 4 – Container Registry & Builds (ECR + CI/CD)

**Objective:** Create two ECR repos (API, Scraper), refactor the codebase for AWS (dual SQLAlchemy engine, Redis URL, scraper Dockerfile), and wire a GitHub Actions pipeline that builds + pushes images and triggers ECS deployments via OIDC — no static AWS keys anywhere.

**Prerequisites:** Phase 0 (OIDC role).

**Steps:**

1. **ECR repos:**
   ```hcl
   resource "aws_ecr_repository" "api" {
     name                 = "dersforumu-api"
     image_tag_mutability = "IMMUTABLE"
     image_scanning_configuration { scan_on_push = true }
     encryption_configuration { encryption_type="KMS" kms_key=aws_kms_key.main.arn }
   }
   resource "aws_ecr_repository" "scraper" {
     name                 = "dersforumu-scraper"
     image_tag_mutability = "IMMUTABLE"
     image_scanning_configuration { scan_on_push = true }
     encryption_configuration { encryption_type="KMS" kms_key=aws_kms_key.main.arn }
   }
   resource "aws_ecr_lifecycle_policy" "api" {
     repository = aws_ecr_repository.api.name
     policy = jsonencode({rules=[{rulePriority=1,description="keep last 20",selection={tagStatus="any",countType="imageCountMoreThan",countNumber=20},action={type="expire"}}]})
   }
   ```

2. **Code change — `app/config.py`** (additions):
   ```python
   class Settings(BaseSettings):
       # existing fields...
       database_url: str
       database_url_reader: str | None = None     # NEW: Aurora reader endpoint
       redis_url: str                              # NEW: rediss://:token@host:6379/0
       aws_region: str = "eu-central-1"
       cognito_region: str = "eu-central-1"
       user_pool_id: str
       app_client_id: str
       model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)
   ```

3. **Code change — `app/database.py`** (dual engine):
   ```python
   from sqlalchemy import create_engine
   from sqlalchemy.orm import sessionmaker, scoped_session
   from app.config import settings

   engine_writer = create_engine(
       settings.database_url,
       pool_size=10, max_overflow=20, pool_pre_ping=True,
       connect_args={"sslmode": "require"},
   )
   engine_reader = create_engine(
       settings.database_url_reader or settings.database_url,
       pool_size=10, max_overflow=20, pool_pre_ping=True,
       connect_args={"sslmode": "require"},
   )
   SessionWriter = scoped_session(sessionmaker(bind=engine_writer, autoflush=False, autocommit=False))
   SessionReader = scoped_session(sessionmaker(bind=engine_reader, autoflush=False, autocommit=False))

   def get_db_write():
       db = SessionWriter()
       try: yield db
       finally: db.close()

   def get_db_read():
       db = SessionReader()
       try: yield db
       finally: db.close()
   ```
   Use `Depends(get_db_read)` in GET routes, `Depends(get_db_write)` in POST/PUT/DELETE.

4. **Code change — `app/main.py`** (X-Ray middleware):
   ```python
   from aws_xray_sdk.core import xray_recorder, patch_all
   from aws_xray_sdk.ext.fastapi.middleware import XRayMiddleware

   xray_recorder.configure(service="dersforumu-api")
   patch_all()
   app.add_middleware(XRayMiddleware, recorder=xray_recorder)
   ```
   Add to `requirements.txt`: `aws-xray-sdk==2.14.0`, `redis==5.0.7`, `boto3==1.34.150`.

5. **New file — `Dockerfile.scraper`:**
   ```dockerfile
   FROM python:3.12-slim
   ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
   WORKDIR /app
   RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
       && rm -rf /var/lib/apt/lists/*
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY app/ ./app/
   COPY suis_scraper.py .
   RUN useradd -u 1001 -m scraper && chown -R scraper /app
   USER scraper
   ENTRYPOINT ["python","suis_scraper.py"]
   ```
   > **Env-var contract for `suis_scraper.py`:** The scraper image contains no
   > credentials. All secrets are injected at ECS task start via Secrets Manager
   > (see Phase 7). The scraper must read the following environment variables
   > at runtime — verify each is consumed via `os.getenv()` or `load_dotenv()`
   > (which reads env vars when no `.env` file is present):
   >
   > | Variable | Secrets Manager key | Description |
   > |---|---|---|
   > | `DATABASE_URL` | `dersforumu/db/master:writer_url::` | Writer endpoint connection string |
   > | `SUIS_USER` | `dersforumu/suis/credentials:username::` | SUIS Banner login username |
   > | `SUIS_PASS` | `dersforumu/suis/credentials:password::` | SUIS Banner login password |
   >
   > No `.env` file is present inside the container image. The existing
   > `load_dotenv()` call at the top of `suis_scraper.py` is harmless (it
   > silently no-ops when no `.env` file exists) and should be kept for local
   > development compatibility.

6. **GitHub Actions workflow — `.github/workflows/deploy.yml`:**
   ```yaml
   name: deploy
   on:
     push: { branches: [main] }
   permissions: { id-token: write, contents: read }
   jobs:
     build:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: aws-actions/configure-aws-credentials@v4
           with:
             role-to-assume: arn:aws:iam::<acct>:role/gha-dersforumu-deployer
             aws-region: eu-central-1
         - uses: aws-actions/amazon-ecr-login@v2
         - name: Build & push API
           run: |
             docker build -t $ECR/dersforumu-api:${{ github.sha }} -f Dockerfile .
             docker push $ECR/dersforumu-api:${{ github.sha }}
           env: { ECR: <acct>.dkr.ecr.eu-central-1.amazonaws.com }
         - name: Build & push Scraper
           run: |
             docker build -t $ECR/dersforumu-scraper:${{ github.sha }} -f Dockerfile.scraper .
             docker push $ECR/dersforumu-scraper:${{ github.sha }}
         - name: Deploy ECS API (blue/green)
           run: |
             aws ecs update-service --cluster dersforumu --service dersforumu-api \
               --force-new-deployment
   ```

**Verification:**
- `aws ecr describe-repositories` shows both repos.
- `aws ecr describe-images --repository-name dersforumu-api` shows pushed image with `imageScanFindingsSummary`.
- GitHub Actions run succeeds end-to-end on a test commit.

---

## Phase 5 – Frontend Hosting (S3 + CloudFront)

**Objective:** Host the React SPA on a private S3 bucket fronted by CloudFront (OAC), with HTTP/2+3, Brotli, security response headers, SPA error-page rewrites, and a Lambda that invalidates the cache when new bundles are deployed.

**Prerequisites:** Phases 0 (ACM us-east-1, Route 53).

**Steps:**

1. **S3 bucket:**
   ```hcl
   resource "aws_s3_bucket" "frontend" { bucket = "dersforumu-frontend" }
   resource "aws_s3_bucket_versioning" "frontend" {
     bucket = aws_s3_bucket.frontend.id
     versioning_configuration { status = "Enabled" }
   }
   resource "aws_s3_bucket_public_access_block" "frontend" {
     bucket = aws_s3_bucket.frontend.id
     block_public_acls=true block_public_policy=true ignore_public_acls=true restrict_public_buckets=true
   }
   resource "aws_s3_bucket_server_side_encryption_configuration" "frontend" {
     bucket = aws_s3_bucket.frontend.id
     rule { apply_server_side_encryption_by_default { sse_algorithm="aws:kms" kms_master_key_id=aws_kms_key.main.arn } }
   }
   ```

2. **CloudFront OAC + distribution:**
   ```hcl
   resource "aws_cloudfront_origin_access_control" "frontend" {
     name = "dersforumu-frontend-oac"
     origin_access_control_origin_type = "s3"
     signing_behavior = "always"
     signing_protocol = "sigv4"
   }

   resource "aws_cloudfront_response_headers_policy" "sec" {
     name = "dersforumu-sec-headers"
     security_headers_config {
       strict_transport_security { access_control_max_age_sec=63072000 include_subdomains=true preload=true override=true }
       content_type_options      { override=true }
       frame_options             { frame_option="DENY" override=true }
       referrer_policy           { referrer_policy="strict-origin-when-cross-origin" override=true }
       content_security_policy   { content_security_policy="default-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self' https://api.dersforumu.com https://cognito-idp.eu-central-1.amazonaws.com" override=true }
     }
   }

   resource "aws_cloudfront_distribution" "main" {
     enabled             = true
     is_ipv6_enabled     = true
     http_version        = "http2and3"
     price_class         = "PriceClass_All"
     aliases             = [var.domain_name, "www.${var.domain_name}"]
     default_root_object = "index.html"

     origin {
       domain_name              = aws_s3_bucket.frontend.bucket_regional_domain_name
       origin_id                = "s3-frontend"
       origin_access_control_id = aws_cloudfront_origin_access_control.frontend.id
     }
     origin {
       domain_name = aws_lb.api.dns_name
       origin_id   = "alb-api"
       custom_origin_config { http_port=80 https_port=443 origin_protocol_policy="https-only" origin_ssl_protocols=["TLSv1.2"] }
     }

     default_cache_behavior {
       target_origin_id       = "s3-frontend"
       viewer_protocol_policy = "redirect-to-https"
       allowed_methods        = ["GET","HEAD","OPTIONS"]
       cached_methods         = ["GET","HEAD"]
       compress               = true
       cache_policy_id        = "658327ea-f89d-4fab-a63d-7e88639e58f6"  # CachingOptimized
       response_headers_policy_id = aws_cloudfront_response_headers_policy.sec.id
     }
     ordered_cache_behavior {
       path_pattern           = "/api/*"
       target_origin_id       = "alb-api"
       viewer_protocol_policy = "https-only"
       allowed_methods        = ["GET","HEAD","OPTIONS","PUT","POST","PATCH","DELETE"]
       cached_methods         = ["GET","HEAD"]
       cache_policy_id        = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"  # CachingDisabled
       origin_request_policy_id = "216adef6-5c7f-47e4-b989-5492eafa07d3" # AllViewer
     }
     ordered_cache_behavior {
       path_pattern           = "/assets/*"
       target_origin_id       = "s3-frontend"
       viewer_protocol_policy = "redirect-to-https"
       allowed_methods        = ["GET","HEAD"]
       cached_methods         = ["GET","HEAD"]
       compress               = true
       cache_policy_id        = "658327ea-f89d-4fab-a63d-7e88639e58f6"
     }

     custom_error_response { error_code=403 response_code=200 response_page_path="/index.html" }
     custom_error_response { error_code=404 response_code=200 response_page_path="/index.html" }

     restrictions { geo_restriction { restriction_type="none" } }
     viewer_certificate {
       acm_certificate_arn      = var.acm_cf_arn
       ssl_support_method       = "sni-only"
       minimum_protocol_version = "TLSv1.2_2021"
     }
     web_acl_id = aws_wafv2_web_acl.cf.arn   # set in Phase 9
   }

   data "aws_iam_policy_document" "frontend_oac" {
     statement {
       actions   = ["s3:GetObject"]
       resources = ["${aws_s3_bucket.frontend.arn}/*"]
       principals { type="Service" identifiers=["cloudfront.amazonaws.com"] }
       condition  { test="StringEquals" variable="AWS:SourceArn" values=[aws_cloudfront_distribution.main.arn] }
     }
   }
   resource "aws_s3_bucket_policy" "frontend" {
     bucket = aws_s3_bucket.frontend.id
     policy = data.aws_iam_policy_document.frontend_oac.json
   }
   ```

3. **Cache-invalidation Lambda** (triggered by S3 `s3:ObjectCreated:*` on `index.html`):
   ```python
   import boto3, os
   cf = boto3.client("cloudfront")
   def handler(event, ctx):
       cf.create_invalidation(
         DistributionId=os.environ["DIST_ID"],
         InvalidationBatch={"Paths":{"Quantity":1,"Items":["/index.html"]},"CallerReference":event["Records"][0]["eventTime"]}
       )
   ```

4. **Route 53 alias records:**
   ```hcl
   resource "aws_route53_record" "root" {
     zone_id = var.hosted_zone_id name = var.domain_name type="A"
     alias { name=aws_cloudfront_distribution.main.domain_name zone_id=aws_cloudfront_distribution.main.hosted_zone_id evaluate_target_health=false }
   }
   resource "aws_route53_record" "root_aaaa" {
     zone_id = var.hosted_zone_id name = var.domain_name type="AAAA"
     alias { name=aws_cloudfront_distribution.main.domain_name zone_id=aws_cloudfront_distribution.main.hosted_zone_id evaluate_target_health=false }
   }
   ```

**Verification:**
- `curl -I https://dersforumu.com` returns 200 with `strict-transport-security`, `content-security-policy` headers.
- `curl https://dersforumu.com/nonexistent-route` returns the SPA index (200).
- Uploading a new `index.html` triggers a CloudFront invalidation visible in `aws cloudfront list-invalidations --distribution-id ...`.

---

## Phase 6 – Compute (ALB + ECS Fargate API)

**Objective:** Run the FastAPI backend as an ECS Fargate service behind an internet-facing ALB, with secrets injected from Secrets Manager, structured JSON logs to CloudWatch, X-Ray sidecar, blue/green CodeDeploy releases, and request/CPU-driven auto-scaling.

**Prerequisites:** Phases 1, 2, 3, 4.

**Steps:**

1. **ALB + target group + listeners:**
   ```hcl
   resource "aws_lb" "api" {
     name               = "${var.project}-alb"
     internal           = false
     load_balancer_type = "application"
     security_groups    = [aws_security_group.alb.id]
     subnets            = aws_subnet.public[*].id
     drop_invalid_header_fields = true
     access_logs { bucket = aws_s3_bucket.logs.id prefix="alb" enabled=true }
   }
   resource "aws_lb_target_group" "api" {
     name        = "${var.project}-api-tg"
     port        = 8000
     protocol    = "HTTP"
     vpc_id      = aws_vpc.main.id
     target_type = "ip"
     deregistration_delay = 30
     health_check { path="/health" matcher="200" interval=15 timeout=5 healthy_threshold=2 unhealthy_threshold=3 }
   }
   resource "aws_lb_target_group" "api_green" {
     # identical spec - used by CodeDeploy blue/green
     name        = "${var.project}-api-tg-green"
     port=8000 protocol="HTTP" vpc_id=aws_vpc.main.id target_type="ip"
     health_check { path="/health" matcher="200" }
   }
   resource "aws_lb_listener" "http" {
     load_balancer_arn = aws_lb.api.arn port=80 protocol="HTTP"
     default_action { type="redirect" redirect { port="443" protocol="HTTPS" status_code="HTTP_301" } }
   }
   resource "aws_lb_listener" "https" {
     load_balancer_arn = aws_lb.api.arn port=443 protocol="HTTPS"
     ssl_policy = "ELBSecurityPolicy-TLS13-1-2-2021-06"
     certificate_arn = var.acm_alb_arn
     default_action { type="forward" target_group_arn = aws_lb_target_group.api.arn }
   }
   ```

2. **ECS cluster:**
   ```hcl
   resource "aws_ecs_cluster" "main" {
     name = var.project
     setting { name="containerInsights" value="enabled" }
   }
   resource "aws_ecs_cluster_capacity_providers" "main" {
     cluster_name       = aws_ecs_cluster.main.name
     capacity_providers = ["FARGATE","FARGATE_SPOT"]
     default_capacity_provider_strategy { capacity_provider="FARGATE" weight=1 base=3 }
   }
   ```

3. **IAM roles:**
   ```hcl
   data "aws_iam_policy_document" "ecs_assume" {
     statement { actions=["sts:AssumeRole"] principals { type="Service" identifiers=["ecs-tasks.amazonaws.com"] } }
   }
   resource "aws_iam_role" "task_exec" {
     name = "ecsTaskExecutionRole-dersforumu"
     assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
   }
   resource "aws_iam_role_policy_attachment" "task_exec_managed" {
     role       = aws_iam_role.task_exec.name
     policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
   }
   resource "aws_iam_role_policy" "task_exec_secrets" {
     role = aws_iam_role.task_exec.id
     policy = jsonencode({Version="2012-10-17",Statement=[
       {Effect="Allow",Action=["secretsmanager:GetSecretValue"],Resource=[
         aws_secretsmanager_secret.db_master.arn,aws_secretsmanager_secret.jwt.arn,
         aws_secretsmanager_secret.ses.arn,aws_secretsmanager_secret.cognito.arn,
         aws_secretsmanager_secret.redis_auth.arn,aws_secretsmanager_secret.suis.arn]},
       {Effect="Allow",Action=["kms:Decrypt"],Resource=[aws_kms_key.main.arn]},
       {Effect="Allow",Action=["ssm:GetParameters"],Resource=["arn:aws:ssm:eu-central-1:*:parameter/dersforumu/*"]}
     ]})
   }

   resource "aws_iam_role" "task_api" {
     name = "ecsTaskRole-dersforumu-api"
     assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
   }
   resource "aws_iam_role_policy" "task_api" {
     role = aws_iam_role.task_api.id
     policy = jsonencode({Version="2012-10-17",Statement=[
       {Effect="Allow",Action=["ses:SendEmail","ses:SendRawEmail"],Resource="*"},
       {Effect="Allow",Action=["cognito-idp:AdminGetUser","cognito-idp:AdminInitiateAuth","cognito-idp:SignUp","cognito-idp:ConfirmSignUp"],Resource=aws_cognito_user_pool.main.arn},
       {Effect="Allow",Action=["xray:PutTraceSegments","xray:PutTelemetryRecords"],Resource="*"},
       {Effect="Allow",Action=["cloudwatch:PutMetricData"],Resource="*"}
     ])
   }
   ```

4. **CloudWatch log group:**
   ```hcl
   resource "aws_cloudwatch_log_group" "api" { name="/ecs/dersforumu-api" retention_in_days=30 kms_key_id=aws_kms_key.main.arn }
   ```

5. **ECS task definition JSON** (`infra/taskdef/api.json`):
   ```json
   {
     "family": "dersforumu-api",
     "networkMode": "awsvpc",
     "requiresCompatibilities": ["FARGATE"],
     "cpu": "1024",
     "memory": "2048",
     "executionRoleArn": "arn:aws:iam::ACCT:role/ecsTaskExecutionRole-dersforumu",
     "taskRoleArn": "arn:aws:iam::ACCT:role/ecsTaskRole-dersforumu-api",
     "runtimePlatform": { "cpuArchitecture": "ARM64", "operatingSystemFamily": "LINUX" },
     "containerDefinitions": [
       {
         "name": "api",
         "image": "ACCT.dkr.ecr.eu-central-1.amazonaws.com/dersforumu-api:IMAGE_TAG",
         "essential": true,
         "portMappings": [{ "containerPort": 8000, "protocol": "tcp" }],
         "environment": [
           { "name": "AWS_REGION", "value": "eu-central-1" },
           { "name": "AWS_XRAY_DAEMON_ADDRESS", "value": "127.0.0.1:2000" },
           { "name": "ALLOWED_EMAIL_DOMAIN", "value": "sabanciuniv.edu" },
           { "name": "OTP_TTL_MINUTES", "value": "5" }
         ],
         "secrets": [
           { "name": "DATABASE_URL",        "valueFrom": "arn:aws:secretsmanager:eu-central-1:ACCT:secret:dersforumu/db/master:writer_url::" },
           { "name": "DATABASE_URL_READER", "valueFrom": "arn:aws:secretsmanager:eu-central-1:ACCT:secret:dersforumu/db/master:reader_url::" },
           { "name": "JWT_SECRET",          "valueFrom": "arn:aws:secretsmanager:eu-central-1:ACCT:secret:dersforumu/jwt/secret:value::" },
           { "name": "REDIS_URL",           "valueFrom": "arn:aws:secretsmanager:eu-central-1:ACCT:secret:dersforumu/redis/authtoken:url::" },
           { "name": "SMTP_USER",           "valueFrom": "arn:aws:secretsmanager:eu-central-1:ACCT:secret:dersforumu/ses/smtp:user::" },
           { "name": "SMTP_PASSWORD",       "valueFrom": "arn:aws:secretsmanager:eu-central-1:ACCT:secret:dersforumu/ses/smtp:password::" },
           { "name": "USER_POOL_ID",        "valueFrom": "arn:aws:secretsmanager:eu-central-1:ACCT:secret:dersforumu/cognito/client:user_pool_id::" },
           { "name": "APP_CLIENT_ID",       "valueFrom": "arn:aws:secretsmanager:eu-central-1:ACCT:secret:dersforumu/cognito/client:app_client_id::" }
         ],
         "logConfiguration": {
           "logDriver": "awslogs",
           "options": {
             "awslogs-group": "/ecs/dersforumu-api",
             "awslogs-region": "eu-central-1",
             "awslogs-stream-prefix": "api",
             "mode": "non-blocking"
           }
         },
         "healthCheck": {
           "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
           "interval": 15, "timeout": 5, "retries": 3, "startPeriod": 30
         },
         "dependsOn": [{ "containerName": "xray", "condition": "START" }]
       },
       {
         "name": "xray",
         "image": "public.ecr.aws/xray/aws-xray-daemon:3.x",
         "essential": false,
         "cpu": 32,
         "memoryReservation": 256,
         "portMappings": [{ "containerPort": 2000, "protocol": "udp" }],
         "logConfiguration": {
           "logDriver": "awslogs",
           "options": {
             "awslogs-group": "/ecs/dersforumu-api",
             "awslogs-region": "eu-central-1",
             "awslogs-stream-prefix": "xray"
           }
         }
       }
     ]
   }
   ```

6. **ECS service** (`infra/ecs_service.tf`):
   ```hcl
   resource "aws_ecs_service" "api" {
     name            = "dersforumu-api"
     cluster         = aws_ecs_cluster.main.id
     task_definition = aws_ecs_task_definition.api.arn
     desired_count   = 3
     launch_type     = "FARGATE"
     platform_version = "LATEST"
     deployment_controller { type = "CODE_DEPLOY" }
     deployment_circuit_breaker { enable=true rollback=true }
     deployment_minimum_healthy_percent = 100
     deployment_maximum_percent         = 200
     enable_execute_command             = true
     network_configuration {
       subnets          = aws_subnet.app[*].id
       security_groups  = [aws_security_group.api.id]
       assign_public_ip = false
     }
     load_balancer { target_group_arn = aws_lb_target_group.api.arn container_name="api" container_port=8000 }
     availability_zone_rebalancing = "ENABLED"
     lifecycle { ignore_changes = [task_definition, load_balancer, desired_count] }
   }
   ```

7. **Auto-scaling:**
   ```hcl
   resource "aws_appautoscaling_target" "api" {
     max_capacity=12 min_capacity=3
     resource_id="service/${aws_ecs_cluster.main.name}/${aws_ecs_service.api.name}"
     scalable_dimension="ecs:service:DesiredCount" service_namespace="ecs"
   }
   resource "aws_appautoscaling_policy" "cpu" {
     name="cpu60" policy_type="TargetTrackingScaling"
     resource_id=aws_appautoscaling_target.api.resource_id
     scalable_dimension=aws_appautoscaling_target.api.scalable_dimension
     service_namespace=aws_appautoscaling_target.api.service_namespace
     target_tracking_scaling_policy_configuration {
       target_value=60
       predefined_metric_specification { predefined_metric_type="ECSServiceAverageCPUUtilization" }
     }
   }
   resource "aws_appautoscaling_policy" "rcpt" {
     name="rcpt200" policy_type="TargetTrackingScaling"
     resource_id=aws_appautoscaling_target.api.resource_id
     scalable_dimension=aws_appautoscaling_target.api.scalable_dimension
     service_namespace=aws_appautoscaling_target.api.service_namespace
     target_tracking_scaling_policy_configuration {
       target_value=200
       predefined_metric_specification {
         predefined_metric_type="ALBRequestCountPerTarget"
         resource_label="${aws_lb.api.arn_suffix}/${aws_lb_target_group.api.arn_suffix}"
       }
     }
   }
   resource "aws_appautoscaling_scheduled_action" "prewarm" {
     name="prewarm-tr-morning" service_namespace="ecs"
     resource_id=aws_appautoscaling_target.api.resource_id
     scalable_dimension=aws_appautoscaling_target.api.scalable_dimension
     schedule="cron(0 5 ? * MON-FRI *)"  # 08:00 Europe/Istanbul = 05:00 UTC
     scalable_target_action { min_capacity=6 max_capacity=12 }
   }
   ```

8. **CodeDeploy blue/green app** is created and tied to the ECS service + both target groups; GitHub Actions calls `aws deploy create-deployment` with an `appspec.yaml`.

**Verification:**
- `aws ecs describe-services --cluster dersforumu --services dersforumu-api --query 'services[0].{running:runningCount,desired:desiredCount}'` returns 3/3.
- `curl -k https://<alb-dns>/health` returns 200.
- `aws ecs execute-command --cluster dersforumu --task <id> --container api --interactive --command "/bin/sh"` opens a shell via SSM.

---

## Phase 7 – Scheduled Scraper (EventBridge → ECS RunTask)

**Objective:** Run the SUIS scraper as an ephemeral Fargate task on a semester + weekly cron schedule, emitting metrics and alarming on failure or staleness.

**Prerequisites:** Phases 1, 2, 4.

**Steps:**

1. **Scraper task definition (CPU 512, Memory 1024):** same shape as the API task without ALB attachment; image = `dersforumu-scraper:tag`; secrets include `DATABASE_URL` (writer) and `SUIS_USER`/`SUIS_PASS` from `dersforumu/suis/credentials`. Log group `/ecs/dersforumu-scraper`.

2. **EventBridge Scheduler IAM role:**
   ```hcl
   resource "aws_iam_role" "scheduler" {
     name = "${var.project}-scheduler"
     assume_role_policy = jsonencode({Version="2012-10-17",Statement=[{Effect="Allow",Principal={Service="scheduler.amazonaws.com"},Action="sts:AssumeRole"}]})
   }
   resource "aws_iam_role_policy" "scheduler" {
     role = aws_iam_role.scheduler.id
     policy = jsonencode({Version="2012-10-17",Statement=[
       {Effect="Allow",Action=["ecs:RunTask"],Resource=aws_ecs_task_definition.scraper.arn},
       {Effect="Allow",Action=["iam:PassRole"],Resource=[aws_iam_role.task_exec.arn, aws_iam_role.task_scraper.arn]}
     ]})
   }
   ```

3. **Schedules:**
   ```hcl
   resource "aws_scheduler_schedule" "semester" {
     name = "scraper-semester"
     schedule_expression = "cron(0 3 1 1,2,6,9 ? *)"
     flexible_time_window { mode="OFF" }
     target {
       arn      = aws_ecs_cluster.main.arn
       role_arn = aws_iam_role.scheduler.arn
       ecs_parameters {
         task_definition_arn = aws_ecs_task_definition.scraper.arn
         launch_type         = "FARGATE"
         network_configuration {
           subnets          = aws_subnet.app[*].id
           security_groups  = [aws_security_group.api.id]
           assign_public_ip = false
         }
       }
     }
   }
   resource "aws_scheduler_schedule" "weekly" {
     name = "scraper-weekly"
     schedule_expression = "cron(0 4 ? * SUN *)"
     # same target as above
   }
   ```

4. **Scraper metric emission** — append to `suis_scraper.py`:
   ```python
   import boto3, time
   cw = boto3.client("cloudwatch", region_name="eu-central-1")
   def emit(name, value, unit="Count"):
       cw.put_metric_data(Namespace="Dersforumu/Scraper",
         MetricData=[{"MetricName":name,"Value":value,"Unit":unit,"Timestamp":time.time()}])
   # at end of run:
   emit("ScraperRowsInserted", rows)
   emit("ScraperDurationSeconds", duration, "Seconds")
   emit("ScraperLastSuccess", 1)
   ```

5. **Alarms:**
   ```hcl
   resource "aws_cloudwatch_metric_alarm" "scraper_failed" {
     alarm_name = "scraper-failed"
     namespace="AWS/ECS" metric_name="TaskStoppedReason"  # use EventBridge rule on ECS Task State Change instead
     # Cleanest: EventBridge rule matching {"source":["aws.ecs"],"detail-type":["ECS Task State Change"],"detail":{"lastStatus":["STOPPED"],"stopCode":["TaskFailedToStart","EssentialContainerExited"]}} → SNS critical
   }
   resource "aws_cloudwatch_metric_alarm" "scraper_stale" {
     alarm_name="scraper-stale"
     namespace="Dersforumu/Scraper" metric_name="ScraperLastSuccess"
     statistic="Sum" period=86400 evaluation_periods=8 threshold=1 comparison_operator="LessThanThreshold"
     treat_missing_data="breaching"
     alarm_actions=[aws_sns_topic.warn.arn]
   }
   ```

**Verification:**
- `aws scheduler list-schedules` shows both schedules.
- Manual trigger: `aws scheduler get-schedule --name scraper-weekly` then `aws ecs run-task --cluster dersforumu --task-definition dersforumu-scraper:LATEST ...`. Check `/ecs/dersforumu-scraper` logs.
- `aws cloudwatch get-metric-statistics --namespace Dersforumu/Scraper --metric-name ScraperRowsInserted ...` shows datapoints.

---

## Phase 8 – Monitoring & Alarms

**Objective:** Wire end-to-end observability — structured logs with retention, Container Insights, X-Ray tracing, synthetics canary, custom EMF metrics, a unified dashboard, three SNS topics by severity, and every alarm from the architecture document.

**Prerequisites:** Phases 5, 6, 7.

**Steps:**

1. **Log groups** (all with 30 d retention, KMS-encrypted):
   ```hcl
   resource "aws_cloudwatch_log_group" "scraper" { name="/ecs/dersforumu-scraper" retention_in_days=30 kms_key_id=aws_kms_key.main.arn }
   resource "aws_cloudwatch_log_group" "alb"     { name="/aws/applicationelb/dersforumu" retention_in_days=30 }
   resource "aws_cloudwatch_log_group" "rds"     { name="/aws/rds/cluster/dersforumu-aurora/postgresql" retention_in_days=30 }
   resource "aws_cloudwatch_log_group" "waf"     { name="aws-waf-logs-dersforumu" retention_in_days=30 }
   ```

2. **SNS topics:**
   ```hcl
   resource "aws_sns_topic" "critical" { name="dersforumu-alerts-critical" kms_master_key_id=aws_kms_key.main.id }
   resource "aws_sns_topic" "warn"     { name="dersforumu-alerts-warn"     kms_master_key_id=aws_kms_key.main.id }
   resource "aws_sns_topic" "info"     { name="dersforumu-alerts-info"     kms_master_key_id=aws_kms_key.main.id }
   resource "aws_sns_topic_subscription" "email_crit" { topic_arn=aws_sns_topic.critical.arn protocol="email" endpoint="alpnuhoglu2@gmail.com" }
   ```
   Add Chatbot Slack integration via console (Chatbot → Slack workspace → channel `#dersforumu-alerts`, subscribe to all three topics).

3. **Alarms (selected; create all from the architecture doc):**
   ```hcl
   resource "aws_cloudwatch_metric_alarm" "api_cpu_high" {
     alarm_name="api-cpu-high" namespace="AWS/ECS" metric_name="CPUUtilization"
     dimensions={ClusterName=aws_ecs_cluster.main.name,ServiceName=aws_ecs_service.api.name}
     statistic="Average" period=60 evaluation_periods=10 threshold=80
     comparison_operator="GreaterThanThreshold" alarm_actions=[aws_sns_topic.warn.arn]
   }
   resource "aws_cloudwatch_metric_alarm" "api_5xx" {
     alarm_name="api-5xx-rate" namespace="AWS/ApplicationELB" metric_name="HTTPCode_Target_5XX_Count"
     dimensions={LoadBalancer=aws_lb.api.arn_suffix,TargetGroup=aws_lb_target_group.api.arn_suffix}
     statistic="Sum" period=60 evaluation_periods=5 threshold=5
     comparison_operator="GreaterThanThreshold" alarm_actions=[aws_sns_topic.critical.arn]
   }
   resource "aws_cloudwatch_metric_alarm" "api_p99" {
     alarm_name="api-p99-latency" namespace="AWS/ApplicationELB"
     metric_name="TargetResponseTime" extended_statistic="p99" period=60 evaluation_periods=10
     threshold=3 comparison_operator="GreaterThanThreshold"
     dimensions={LoadBalancer=aws_lb.api.arn_suffix,TargetGroup=aws_lb_target_group.api.arn_suffix}
     alarm_actions=[aws_sns_topic.warn.arn]
   }
   resource "aws_cloudwatch_metric_alarm" "healthy_hosts" {
     alarm_name="api-healthy-hosts-low" namespace="AWS/ApplicationELB" metric_name="HealthyHostCount"
     dimensions={LoadBalancer=aws_lb.api.arn_suffix,TargetGroup=aws_lb_target_group.api.arn_suffix}
     statistic="Minimum" period=60 evaluation_periods=2 threshold=2
     comparison_operator="LessThanThreshold" alarm_actions=[aws_sns_topic.critical.arn]
   }
   # DB CPU, DB connections (DatabaseConnections vs max via math expr), ReplicaLag, FailoverEvent,
   # Redis Evictions, OTPVerifyFailures(custom), WAF BlockedRequests, ACM DaysToExpiry, Budget — same pattern.
   ```

4. **Synthetics canary:**
   ```hcl
   resource "aws_synthetics_canary" "health" {
     name = "dersforumu-health" artifact_s3_location="s3://${aws_s3_bucket.logs.id}/canary/"
     execution_role_arn=aws_iam_role.canary.arn runtime_version="syn-nodejs-puppeteer-9.0"
     handler="index.handler" zip_file="canary/health.zip"
     schedule { expression="rate(5 minutes)" }
     run_config { timeout_in_seconds=60 }
     success_retention_period=2 failure_retention_period=14
     start_canary=true
   }
   ```
   `health.js` GETs `https://dersforumu.com/` and `https://dersforumu.com/api/health`.

5. **Dashboard** — `aws cloudwatch put-dashboard --dashboard-name Dersforumu-Prod --dashboard-body file://dashboard.json` containing widgets for: ECS CPU/Mem, ALB request count + 4xx/5xx + p50/p99, Aurora CPU + connections + ReplicaLag, Redis CPU + Evictions, WAF Blocked, Synthetics SuccessPercent, custom OTP/Reviews/Scraper metrics.

6. **Composite alarm** combining `api_5xx OR healthy_hosts < 2` → single critical pager.

7. **Route 53 health check** on `https://dersforumu.com/health` + alarm on `HealthCheckStatus < 1`.

8. **AWS Health → SNS** EventBridge rule: source `aws.health`, target SNS warn.

**Verification:**
- `aws cloudwatch describe-alarms --region eu-central-1 --state-value OK --query 'length(MetricAlarms)' --output text` ≥ 15.
- `aws synthetics get-canary --name dersforumu-health --query 'Canary.Status.State'` → `RUNNING`.
- X-Ray service map (console) shows `dersforumu-api → Aurora`, `→ Redis`, `→ Cognito`.

---

## Phase 9 – Security Hardening

**Objective:** Layer in edge filtering (WAF), audit trails (CloudTrail with Object Lock), threat detection (GuardDuty), drift detection (Config + CIS conformance pack), supply-chain scanning (ECR Inspector), and rotation. Make the system audit-ready.

**Prerequisites:** Phases 5, 6.

**Steps:**

1. **WAF v2 WebACL (scope=CLOUDFRONT, region=us-east-1 provider alias):**
   ```hcl
   resource "aws_wafv2_web_acl" "cf" {
     provider = aws.us_east_1
     name     = "dersforumu-cf"
     scope    = "CLOUDFRONT"
     default_action { allow {} }
     visibility_config { sampled_requests_enabled=true cloudwatch_metrics_enabled=true metric_name="dersforumuCF" }

     dynamic "rule" {
       for_each = toset([
         "AWSManagedRulesCommonRuleSet",
         "AWSManagedRulesKnownBadInputsRuleSet",
         "AWSManagedRulesSQLiRuleSet",
         "AWSManagedRulesAmazonIpReputationList",
         "AWSManagedRulesAnonymousIpList",
         "AWSManagedRulesLinuxRuleSet"
       ])
       content {
         name     = rule.value
         priority = index(["AWSManagedRulesCommonRuleSet","AWSManagedRulesKnownBadInputsRuleSet","AWSManagedRulesSQLiRuleSet","AWSManagedRulesAmazonIpReputationList","AWSManagedRulesAnonymousIpList","AWSManagedRulesLinuxRuleSet"], rule.value)
         override_action { none {} }
         statement { managed_rule_group_statement { name=rule.value vendor_name="AWS" } }
         visibility_config { sampled_requests_enabled=true cloudwatch_metrics_enabled=true metric_name=rule.value }
       }
     }

     rule {
       name="rate-auth" priority=10
       action { block {} }
       statement {
         rate_based_statement {
           limit=100 aggregate_key_type="IP"
           scope_down_statement { byte_match_statement {
             field_to_match { uri_path {} } positional_constraint="STARTS_WITH"
             search_string="/api/auth/" text_transformation { priority=0 type="LOWERCASE" }
           }}
         }
       }
       visibility_config { sampled_requests_enabled=true cloudwatch_metrics_enabled=true metric_name="rateAuth" }
     }
     # STUDENT TRAVEL NOTE: This rule blocks all countries not in the allowlist.
     # Sabancı students studying or travelling abroad will be blocked unless
     # their country is added here. Expand country_codes freely (ISO 3166-1
     # alpha-2). Alternatively, set action { count {} } and monitor
     # CloudWatch metric "geo" for a week before switching to block, to avoid
     # locking out legitimate users. Students can also use a TR-exit VPN as a
     # workaround while their country is not on the list.
     rule {
       name="geo-allow" priority=20
       action { block {} }
       statement { not_statement { statement { geo_match_statement {
         # Current allowlist: Turkey (home), Germany (AWS region/dev team),
         # United States (dev/ops), Great Britain, Netherlands.
         # ADD countries here as needed (e.g., "JP","SE","FR","AU").
         country_codes=["TR","DE","US","GB","NL"]
       } } } }
       visibility_config { sampled_requests_enabled=true cloudwatch_metrics_enabled=true metric_name="geo" }
     }
     rule {
       name="reviews-size" priority=30
       action { block {} }
       statement { size_constraint_statement {
         field_to_match { body {} } comparison_operator="GT" size=8192
         text_transformation { priority=0 type="NONE" }
       }}
       visibility_config { sampled_requests_enabled=true cloudwatch_metrics_enabled=true metric_name="reviewsSize" }
     }
   }
   resource "aws_wafv2_web_acl_logging_configuration" "cf" {
     provider = aws.us_east_1
     log_destination_configs = [aws_cloudwatch_log_group.waf.arn]
     resource_arn = aws_wafv2_web_acl.cf.arn
   }
   ```
   (Attached via `web_acl_id` on the CloudFront distribution in Phase 5.)

2. **CloudTrail with Object Lock S3:**
   ```hcl
   resource "aws_s3_bucket" "trail" { bucket="dersforumu-cloudtrail" object_lock_enabled=true }
   resource "aws_s3_bucket_object_lock_configuration" "trail" {
     bucket = aws_s3_bucket.trail.id
     rule { default_retention { mode="COMPLIANCE" days=365 } }
   }
   resource "aws_cloudtrail" "main" {
     name="dersforumu-trail" s3_bucket_name=aws_s3_bucket.trail.id
     is_multi_region_trail=true include_global_service_events=true enable_log_file_validation=true
     kms_key_id=aws_kms_key.main.arn
     event_selector { read_write_type="All" include_management_events=true
       data_resource { type="AWS::S3::Object" values=["${aws_s3_bucket.frontend.arn}/"] }
     }
   }
   ```

3. **GuardDuty:**
   ```hcl
   resource "aws_guardduty_detector" "main" { enable=true finding_publishing_frequency="FIFTEEN_MINUTES" }
   resource "aws_cloudwatch_event_rule" "gd" {
     name="guardduty-findings" event_pattern=jsonencode({source=["aws.guardduty"],"detail-type"=["GuardDuty Finding"]})
   }
   resource "aws_cloudwatch_event_target" "gd" {
     rule=aws_cloudwatch_event_rule.gd.name arn=aws_sns_topic.critical.arn
   }
   ```

4. **AWS Config + CIS conformance pack:**
   ```bash
   aws configservice put-configuration-recorder --configuration-recorder name=default,roleARN=$ROLE \
     --recording-group allSupported=true,includeGlobalResourceTypes=true
   aws configservice put-delivery-channel --delivery-channel name=default,s3BucketName=dersforumu-config
   aws configservice start-configuration-recorder --configuration-recorder-name default
   aws configservice put-conformance-pack --conformance-pack-name CIS --template-s3-uri s3://aws-config-conformance-packs/Operational-Best-Practices-for-CIS.yaml
   ```

5. **ECR Inspector v2:** `aws inspector2 enable --resource-types ECR --account-ids $(aws sts get-caller-identity --query Account --output text)`.

6. **ACM expiry alarm** (metric `DaysToExpiry` on each cert ARN, threshold 30) → SNS warn.

7. **IAM least-privilege checklist:** run `aws iam generate-service-last-accessed-details` on every role created; remove unused services. Enable Access Analyzer.

**Verification:**
- `aws wafv2 list-web-acls --scope CLOUDFRONT --region us-east-1` shows the ACL; CloudFront distribution has it attached.
- `aws guardduty list-detectors` returns one ID; trigger a sample finding `aws guardduty create-sample-findings --detector-id ...` — appears in SNS critical.
- `aws cloudtrail get-trail-status --name dersforumu-trail` → `IsLogging: true`.
- `aws configservice describe-conformance-packs` lists CIS, non-compliant resource count visible.

---

## Phase 10 – DNS Cutover & Go-Live

**Objective:** Safely migrate from dev to production traffic: harden migrations with an advisory lock, take a manual snapshot, do a canary rollout via CodeDeploy, flip Route 53, run smoke tests, then enable cross-region snapshot copy for DR.

**Prerequisites:** All previous phases.

**Steps:**

1. **Alembic advisory lock** — wrap `alembic upgrade head` in `start.sh`:
   ```bash
   #!/bin/bash
   set -e
   python - <<'PY'
   from sqlalchemy import create_engine, text
   import os, subprocess, sys
   eng = create_engine(os.environ["DATABASE_URL"])
   with eng.connect() as c:
       got = c.execute(text("SELECT pg_try_advisory_lock(727271)")).scalar()
       if not got:
           print("Another task is migrating; skipping."); sys.exit(0)
       try:
           subprocess.check_call(["alembic","upgrade","head"])
       finally:
           c.execute(text("SELECT pg_advisory_unlock(727271)"))
   PY
   exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
   ```

2. **Pre-cutover snapshot:**
   ```bash
   aws rds create-db-cluster-snapshot --db-cluster-identifier dersforumu-aurora \
     --db-cluster-snapshot-identifier dersforumu-precutover-$(date +%Y%m%d)
   ```

3. **Canary CodeDeploy** — `appspec.yaml`:
   ```yaml
   version: 0.0
   Resources:
     - TargetService:
         Type: AWS::ECS::Service
         Properties:
           TaskDefinition: <TASKDEF_ARN>
           LoadBalancerInfo: { ContainerName: api, ContainerPort: 8000 }
   ```
   Deployment configuration: `CodeDeployDefault.ECSCanary10Percent5Minutes` (10% → wait 5 min → 100%). Promote manually if alarms quiet.

4. **Route 53 cutover** — alias was created in Phase 5; final step is to remove any temporary `dev.dersforumu.com` records and lower TTL on apex to 60 s for 24 h before cutover, then back to 300 s.

5. **Smoke test script** — see Post-Deployment Validation Script below; run it post-cutover.

6. **Cross-region DR — automated snapshot copy to eu-west-1.**

   Two equivalent approaches are available. **AWS Backup** (Option A) is simpler
   to operate; the **Lambda approach** (Option B) is shown for full transparency.
   Choose one — do not run both.

   **Option A — AWS Backup (recommended, no Lambda required):**
   ```bash
   # Create a vault in eu-west-1 first
   aws backup create-backup-vault --backup-vault-name dersforumu-dr \
     --region eu-west-1

   # Create a plan that copies Aurora snapshots to eu-west-1 weekly
   aws backup create-backup-plan --region eu-central-1 --backup-plan '{
     "BackupPlanName": "dersforumu-dr-copy",
     "Rules": [{
       "RuleName": "weekly-aurora-dr",
       "TargetBackupVaultName": "dersforumu-primary",
       "ScheduleExpression": "cron(0 2 ? * SUN *)",
       "Lifecycle": {"DeleteAfterDays": 35},
       "CopyActions": [{
         "DestinationBackupVaultArn": "arn:aws:backup:eu-west-1:ACCT:backup-vault:dersforumu-dr",
         "Lifecycle": {"DeleteAfterDays": 35}
       }]
     }]
   }'
   # Assign the Aurora cluster to the plan
   aws backup create-backup-selection --region eu-central-1 \
     --backup-plan-id <plan-id-from-above> \
     --backup-selection '{
       "SelectionName": "aurora-cluster",
       "IamRoleArn": "arn:aws:iam::ACCT:role/AWSBackupDefaultServiceRole",
       "Resources": ["arn:aws:rds:eu-central-1:ACCT:cluster:dersforumu-aurora"]
     }'
   ```

   **Option B — Lambda + EventBridge (full IaC, `infra/dr_snapshot_copy.tf`):**
   ```hcl
   # IAM role for the copy Lambda
   resource "aws_iam_role" "snapshot_copy" {
     name = "dersforumu-snapshot-copy-lambda"
     assume_role_policy = jsonencode({
       Version = "2012-10-17"
       Statement = [{
         Effect    = "Allow"
         Principal = { Service = "lambda.amazonaws.com" }
         Action    = "sts:AssumeRole"
       }]
     })
   }

   resource "aws_iam_role_policy" "snapshot_copy" {
     name = "snapshot-copy-policy"
     role = aws_iam_role.snapshot_copy.id
     policy = jsonencode({
       Version = "2012-10-17"
       Statement = [
         {
           Sid    = "CopySnapshot"
           Effect = "Allow"
           Action = [
             "rds:CopyDBClusterSnapshot",
             "rds:DescribeDBClusterSnapshots",
             "rds:AddTagsToResource"
           ]
           Resource = "*"
         },
         {
           Sid    = "KMSForDestinationRegion"
           Effect = "Allow"
           Action = ["kms:Decrypt", "kms:GenerateDataKey", "kms:CreateGrant", "kms:DescribeKey"]
           # The KMS key ARN in eu-west-1 used to encrypt the copied snapshot.
           # Create this key in eu-west-1 beforehand: aws kms create-key --region eu-west-1
           Resource = "arn:aws:kms:eu-west-1:${data.aws_caller_identity.current.account_id}:key/*"
         },
         {
           Sid      = "Logs"
           Effect   = "Allow"
           Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
           Resource = "arn:aws:logs:*:*:*"
         }
       ]
     })
   }

   # Lambda function (inline Python)
   resource "aws_lambda_function" "snapshot_copy" {
     function_name    = "dersforumu-snapshot-copy"
     role             = aws_iam_role.snapshot_copy.arn
     handler          = "index.handler"
     runtime          = "python3.12"
     timeout          = 60
     filename         = data.archive_file.snapshot_copy_zip.output_path
     source_code_hash = data.archive_file.snapshot_copy_zip.output_base64sha256

     environment {
       variables = {
         DEST_REGION    = "eu-west-1"
         DEST_KMS_KEY   = "arn:aws:kms:eu-west-1:${data.aws_caller_identity.current.account_id}:key/<eu-west-1-key-id>"
         CLUSTER_ID     = "dersforumu-aurora"
       }
     }
   }

   data "archive_file" "snapshot_copy_zip" {
     type        = "zip"
     output_path = "${path.module}/snapshot_copy.zip"
     source {
       filename = "index.py"
       content  = <<-PYTHON
         import boto3, os, datetime

         def handler(event, context):
             detail = event.get("detail", {})
             # Only act on automated cluster snapshots for our cluster
             src_arn = detail.get("SourceArn", "")
             if os.environ["CLUSTER_ID"] not in src_arn:
                 print(f"Ignoring snapshot for {src_arn}")
                 return
             snapshot_id = detail.get("SourceIdentifier", "")
             dest_id = snapshot_id + "-dr-" + datetime.datetime.utcnow().strftime("%Y%m%d%H%M")
             src_region = os.environ.get("AWS_REGION", "eu-central-1")
             dest_region = os.environ["DEST_REGION"]
             kms_key = os.environ["DEST_KMS_KEY"]

             rds = boto3.client("rds", region_name=dest_region)
             resp = rds.copy_db_cluster_snapshot(
                 SourceDBClusterSnapshotIdentifier=f"arn:aws:rds:{src_region}:{boto3.client('sts').get_caller_identity()['Account']}:cluster-snapshot:{snapshot_id}",
                 TargetDBClusterSnapshotIdentifier=dest_id,
                 KmsKeyId=kms_key,
                 CopyTags=True,
                 SourceRegion=src_region,
             )
             print(f"Copy initiated: {resp['DBClusterSnapshot']['DBClusterSnapshotIdentifier']}")
       PYTHON
     }
   }

   # EventBridge rule: fire when Aurora creates an automated cluster snapshot
   resource "aws_cloudwatch_event_rule" "aurora_snapshot_created" {
     name        = "dersforumu-aurora-snapshot-created"
     description = "Triggers DR copy Lambda on each new Aurora automated snapshot"
     event_pattern = jsonencode({
       source        = ["aws.rds"]
       "detail-type" = ["RDS DB Cluster Snapshot Event"]
       detail        = {
         EventCategories = ["creation"]
         SourceIdentifier = [{ prefix = "rds:dersforumu-aurora-" }]
       }
     })
   }

   resource "aws_cloudwatch_event_target" "aurora_snapshot_copy_lambda" {
     rule      = aws_cloudwatch_event_rule.aurora_snapshot_created.name
     target_id = "SnapshotCopyLambda"
     arn       = aws_lambda_function.snapshot_copy.arn
   }

   resource "aws_lambda_permission" "allow_eventbridge" {
     statement_id  = "AllowEventBridgeInvoke"
     action        = "lambda:InvokeFunction"
     function_name = aws_lambda_function.snapshot_copy.function_name
     principal     = "events.amazonaws.com"
     source_arn    = aws_cloudwatch_event_rule.aurora_snapshot_created.arn
   }
   ```

   **Verification (Option B):** After the next Aurora automated snapshot:
   ```bash
   aws rds describe-db-cluster-snapshots --region eu-west-1 \
     --query 'DBClusterSnapshots[?contains(DBClusterSnapshotIdentifier,`-dr-`)].{ID:DBClusterSnapshotIdentifier,Status:Status}' \
     --output table
   # Expected: at least one row with Status=available
   ```

**Verification:**
- Pre-cutover snapshot present: `aws rds describe-db-cluster-snapshots --query 'DBClusterSnapshots[?starts_with(DBClusterSnapshotIdentifier,`dersforumu-precutover-`)].Status'` → `available`.
- `dig dersforumu.com` resolves to CloudFront IPs.
- Smoke test script exits 0.

---

## Summary Checklist

**Identity/Account:** Root MFA, alias, Admin user with MFA, OIDC IdP, `gha-dersforumu-deployer` role, IAM Access Analyzer.
**State/CI:** `dersforumu-tfstate` S3 + `dersforumu-tflock` DynamoDB; GitHub Actions deploy workflow; gitleaks pre-commit.
**Networking:** VPC `10.20.0.0/16`; 9 subnets; IGW; 2 (or 3) NAT GWs + EIPs; 4 route tables; 5 SGs (alb, api, db, redis, endpoints); 1 gateway + 8 interface VPC endpoints; NACLs per tier.
**KMS:** `alias/dersforumu` CMK with rotation.
**Data:** Aurora PG16 cluster (writer+reader r6g.large Multi-AZ), DB subnet/parameter groups, Enhanced Monitoring role; ElastiCache Redis t4g.small primary+replica Multi-AZ; 6 Secrets Manager entries + DB rotation Lambda; SSM Parameter Store entries.
**Identity/Mail:** Cognito user pool + app client + pre-sign-up Lambda; SES domain identity + DKIM (×3) + SPF + DMARC + configuration set.
**Registry/CI:** ECR `dersforumu-api`, `dersforumu-scraper` (KMS, scan-on-push, immutable, lifecycle).
**Frontend:** S3 `dersforumu-frontend` (BPA + KMS + versioning) + OAC + bucket policy; CloudFront distribution + Response Headers policy + SPA error pages; cache-invalidation Lambda; Route 53 A/AAAA aliases.
**Compute:** ALB + 2 target groups (blue/green) + HTTP/HTTPS listeners; ECS cluster (Container Insights, FARGATE+FARGATE_SPOT); `ecsTaskExecutionRole-dersforumu`; `ecsTaskRole-dersforumu-api`; API task def with X-Ray sidecar; ECS service (CodeDeploy controller, circuit breaker); App Auto Scaling (CPU + RCPT) + scheduled pre-warm; CodeDeploy app/deployment group.
**Scraper:** Scraper task def; `ecsTaskRole-dersforumu-scraper`; EventBridge Scheduler role + 2 schedules; failure EventBridge rule → SNS; staleness alarm.
**Observability:** Log groups (api, scraper, ALB, RDS, WAF) with KMS + 30 d; SNS critical/warn/info + Slack via Chatbot; ≥15 CloudWatch alarms; Synthetics canary; Dashboard `Dersforumu-Prod`; Route 53 health check; X-Ray service map.
**Security:** WAF v2 ACL (6 managed + 3 custom rules) attached to CloudFront + logs; CloudTrail multi-region with Object Lock S3; GuardDuty + sample finding rule; AWS Config recorder + CIS conformance pack; Inspector v2 on ECR; ACM expiry alarm; Access Analyzer.
**Go-Live:** Alembic advisory lock; pre-cutover snapshot; CodeDeploy canary; Route 53 cutover; cross-region snapshot copy to eu-west-1.

---

## Post-Deployment Validation Script

`scripts/validate.sh`:
```bash
#!/usr/bin/env bash
# Self-contained validation script — no jq dependency.
# All AWS responses are parsed via `aws --query` and `--output text`.
# The only external dependencies are: aws CLI v2, curl, grep, bash 4+.
set -euo pipefail
REGION=eu-central-1
DOMAIN=dersforumu.com
CLUSTER=dersforumu
SERVICE=dersforumu-api
fail() { echo "FAIL: $*" >&2; exit 1; }
ok()   { echo "OK:   $*"; }

# Dependency check — warn if jq is present (not required) but never used below
command -v aws  >/dev/null || fail "aws CLI not found — install AWS CLI v2"
command -v curl >/dev/null || fail "curl not found"

# 1. CloudFront 200 on / and /api/health
code=$(curl -s -o /dev/null -w '%{http_code}' "https://${DOMAIN}/")
[[ "$code" == "200" ]] || fail "root returned $code"; ok "root 200"
code=$(curl -s -o /dev/null -w '%{http_code}' "https://${DOMAIN}/api/health")
[[ "$code" == "200" ]] || fail "/api/health returned $code"; ok "api/health 200"

# 2. Cognito rejects non-allowed domain
CLIENT=$(aws ssm get-parameter --region "$REGION" \
  --name /dersforumu/cognito/client_id \
  --query Parameter.Value --output text)
out=$(aws cognito-idp sign-up --region "$REGION" \
  --client-id "$CLIENT" \
  --username "reject-$(date +%s)@gmail.com" \
  --password 'Aa1!Aa1!Aa1!' \
  --user-attributes Name=email,Value=reject@gmail.com 2>&1 || true)
echo "$out" | grep -qi "sabanciuniv\|PreSignUp\|failed with error\|NotAuthorizedException" \
  || fail "Cognito did not reject non-allowed domain — got: $out"
ok "Cognito rejected non-sabanciuniv.edu"

# 3. /api/health reports DB ping
# /health returns JSON: {"status":"ok","database":"ok"}
# Parse with aws-cli-free grep instead of jq
health_body=$(curl -sf "https://${DOMAIN}/api/health") \
  || fail "/api/health did not return 200"
echo "$health_body" | grep -q '"database".*"ok"' \
  || fail "DB ping not ok — health body: $health_body"
ok "DB ping ok"

# 4. ECS has 3 running tasks
running=$(aws ecs describe-services --region "$REGION" \
  --cluster "$CLUSTER" --services "$SERVICE" \
  --query 'services[0].runningCount' --output text)
[[ "$running" -ge 3 ]] || fail "ECS running tasks = $running (expected ≥ 3)"; ok "ECS running=$running"

# 5. Aurora available
st=$(aws rds describe-db-clusters --region "$REGION" \
  --db-cluster-identifier dersforumu-aurora \
  --query 'DBClusters[0].Status' --output text)
[[ "$st" == "available" ]] || fail "Aurora status=$st"; ok "Aurora available"

# 6. Redis available
st=$(aws elasticache describe-replication-groups --region "$REGION" \
  --replication-group-id dersforumu-redis \
  --query 'ReplicationGroups[0].Status' --output text)
[[ "$st" == "available" ]] || fail "Redis status=$st"; ok "Redis available"

# 7. No alarms in ALARM state (uses --query length(), no jq)
in_alarm=$(aws cloudwatch describe-alarms --region "$REGION" \
  --state-value ALARM \
  --query 'length(MetricAlarms)' --output text)
[[ "$in_alarm" == "0" ]] || fail "$in_alarm alarm(s) in ALARM state — check CloudWatch console"
ok "All alarms in OK/INSUFFICIENT_DATA state"

# 8. ECR images present
for r in dersforumu-api dersforumu-scraper; do
  n=$(aws ecr describe-images --region "$REGION" \
    --repository-name "$r" \
    --query 'length(imageDetails)' --output text)
  [[ "$n" -ge 1 ]] || fail "ECR repo $r is empty — push an image first"
  ok "ECR $r has $n image(s)"
done

# 9. All 6 Secrets Manager secrets exist
for s in dersforumu/db/master dersforumu/jwt/secret dersforumu/ses/smtp \
         dersforumu/cognito/client dersforumu/redis/authtoken dersforumu/suis/credentials; do
  aws secretsmanager describe-secret --region "$REGION" --secret-id "$s" \
    --query 'Name' --output text >/dev/null \
    || fail "Missing secret: $s"
  ok "Secret $s exists"
done

echo ""
echo "======================================="
echo "  ALL CHECKS PASSED — system is live"
echo "======================================="
```
