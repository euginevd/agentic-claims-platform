variable "region" {
  description = "AWS region for the platform"
  type        = string
  default     = "ap-southeast-2"
}

variable "prefix" {
  description = "Prefix for every resource name; the apply role can only manage resources with it"
  type        = string
  default     = "acp"
}

variable "github_repo" {
  description = "GitHub repository allowed to assume the CI/CD roles, as owner/name"
  type        = string
  default     = "euginevd/agentic-claims-platform"
}

variable "monthly_budget_usd" {
  description = "Monthly cost alarm threshold in USD"
  type        = string
  default     = "20"
}

variable "budget_email" {
  description = "Email address for budget alerts"
  type        = string
}
