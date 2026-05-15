terraform {
  required_version = ">= 1.9.0"
  required_providers {
    aws    = { source = "hashicorp/aws", version = "~> 5.60" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
    archive = { source = "hashicorp/archive", version = "~> 2.4" }
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

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
