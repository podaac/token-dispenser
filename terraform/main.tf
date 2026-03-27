terraform {
  backend "s3" {}
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.32"
    }
  }
  required_version = ">= 1.10, < 2.0.0"
}

data "aws_region" "current" {}

provider "aws" {
  ignore_tags {
    key_prefixes = ["gsfc-ngap"]
  }

  default_tags {
    tags = local.default_tags
  }
}

locals {
  prefix  = var.prefix
  environment = var.prefix
  account_id = data.aws_caller_identity.current.account_id

  default_tags = length(var.default_tags) == 0 ? {
    team        = var.team,
    application = var.prefix,
    environment = var.prefix
  } : var.default_tags
}

data "aws_caller_identity" "current" {}