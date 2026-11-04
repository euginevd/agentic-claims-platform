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
  description = "Monthly budget in USD; the forecast alert fires if the month is heading over it"
  type        = string
  default     = "10"
}

variable "alert_thresholds_usd" {
  description = "Actual-spend steps in USD; one email as each is passed"
  type        = list(number)
  default     = [2, 3, 5, 10]
}

variable "budget_email" {
  description = "Email address for budget alerts"
  type        = string
}
