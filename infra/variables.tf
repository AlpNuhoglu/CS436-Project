variable "project"       { default = "dersforumu" }
variable "env"           { default = "prod" }
variable "vpc_cidr"      { default = "10.20.0.0/16" }
variable "azs"           { default = ["eu-central-1a", "eu-central-1b", "eu-central-1c"] }

# Domain: no custom domain — using CloudFront's auto-assigned *.cloudfront.net URL.
# Route 53 hosted zone and ACM certificates are NOT used in this deployment.
# Update these if a real domain is added later.
variable "domain_name"    { default = "" }  # unused
variable "hosted_zone_id" { default = "" }  # unused
variable "acm_cf_arn"     { default = "" }  # unused — CloudFront will use its default cert
variable "acm_alb_arn"    { default = "" }  # unused — ALB uses HTTP internally (behind CF)

# NAT Gateway count: 2 = cost/HA balance
variable "nat_gateway_count" { default = 2 }

# Aurora: "serverless" (Serverless v2, 0.5-4 ACU)
variable "aurora_mode" { default = "serverless" }

# Alert / notification email
variable "alert_email" { default = "alpnuhoglu2@gmail.com" }

# GitHub OIDC
variable "github_repo" { default = "AlpNuhoglu/CS436-Project" }
