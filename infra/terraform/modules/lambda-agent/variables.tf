variable "name" {
  description = "Function name; must start with the project prefix so the apply role can manage it"
  type        = string
}

variable "source_dir" {
  description = "Folder holding the function code (handler.py)"
  type        = string
}

variable "model_id" {
  description = "Bedrock model or inference profile ID the agent calls"
  type        = string
}

variable "bedrock_model_arns" {
  description = "ARNs the agent may invoke: the inference profile and the foundation models behind it"
  type        = list(string)
}

variable "timeout_seconds" {
  description = "Maximum run time for one invocation"
  type        = number
  default     = 300
}

variable "max_concurrency" {
  description = "Reserved concurrency, which caps cost and abuse"
  type        = number
  default     = 1
}

variable "log_retention_days" {
  description = "How long to keep the function's logs"
  type        = number
  default     = 30
}
