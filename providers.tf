
terraform {
  required_version = ">= 1.6.0"

  cloud {
    organization = "rharvey-org"

    workspaces {
      name = "terraform-cloudops-dashboard"
    }
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }

    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

provider "aws" {
  region = var.aws_region
}