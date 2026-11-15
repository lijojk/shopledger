provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project   = var.project
      ManagedBy = "terraform"
    }
  }
}

module "network" {
  source  = "../modules/network"
  project = var.project
}

module "app_server" {
  source              = "../modules/app_server"
  project             = var.project
  vpc_id              = module.network.vpc_id
  subnet_id           = module.network.public_subnet_id
  instance_type       = var.instance_type
  admin_cidr          = var.admin_cidr
  ssh_public_key_path = var.ssh_public_key_path
}

# Warns before money is spent. Credits are excluded, otherwise they hide the real usage.
resource "aws_budgets_budget" "monthly" {
  name         = "${var.project}-monthly"
  budget_type  = "COST"
  limit_amount = var.monthly_budget_usd
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_types {
    include_credit = false
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 50
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.budget_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.budget_email]
  }
}
