terraform {
  backend "s3" {}
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.32"
    }
  }
  required_version = "~> 1.10.4"
}

data "aws_region" "current" {}

provider "aws" {
  region                    = data.aws_region.current.name
  shared_credentials_files  = [var.credentials]
  profile                   = var.profile

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

  default_tags = { #default_tags inside the provider block
    tags = length(var.default_tags) == 0 ? {
      team        = var.team,
      application = var.prefix, # Use var.prefix directly
      environment = var.prefix
    } : var.default_tags
  }
}

data "aws_caller_identity" "current" {}