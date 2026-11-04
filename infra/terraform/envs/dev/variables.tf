variable "model_id" {
  description = "Bedrock inference profile ID for Claude Haiku in Sydney (from the Bedrock console)"
  type        = string
}

variable "bedrock_model_arns" {
  description = "Inference profile ARN plus the foundation model ARNs it routes to"
  type        = list(string)
}
