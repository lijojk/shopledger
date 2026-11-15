variable "region" {
  type    = string
  default = "ap-south-1"
}

variable "project" {
  type    = string
  default = "shopledger"
}

variable "instance_type" {
  type    = string
  default = "t3.micro"
}

variable "admin_cidr" {
  description = "Your public IP with /32. Only this address can use SSH."
  type        = string

  validation {
    condition     = can(cidrhost(var.admin_cidr, 0)) && endswith(var.admin_cidr, "/32")
    error_message = "admin_cidr must be one address, for example 203.0.113.10/32."
  }
}

variable "ssh_public_key_path" {
  type    = string
  default = "~/.ssh/id_ed25519.pub"
}

variable "budget_email" {
  description = "Receives the billing alerts."
  type        = string
}

variable "monthly_budget_usd" {
  type    = string
  default = "5"
}
