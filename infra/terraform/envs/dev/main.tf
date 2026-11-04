terraform {
  required_version = ">= 1.10"
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

  # The bucket name is passed at init time (-backend-config), so no account details are committed.
  backend "s3" {
    key          = "dev/terraform.tfstate"
    region       = "ap-southeast-2"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region = "ap-southeast-2"
  default_tags {
    tags = {
      project     = "agentic-claims-platform"
      environment = "dev"
      managed-by  = "terraform"
    }
  }
}

module "maze_agent" {
  source             = "../../modules/lambda-agent"
  name               = "acp-dev-maze-agent"
  source_dir         = "${path.root}/../../../../app/maze/02_lambda_converse"
  model_id           = var.model_id
  bedrock_model_arns = var.bedrock_model_arns
}
