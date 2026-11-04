# Example values only. In CI these come from GitHub variables (TF_VAR_model_id, TF_VAR_bedrock_model_arns).
# Copy the real IDs from the Bedrock console: Inference and Assessment → Cross-region inference.
model_id = "<inference-profile-id-for-claude-haiku>"

bedrock_model_arns = [
  "arn:aws:bedrock:ap-southeast-2:<account-id>:inference-profile/<inference-profile-id>",
  "arn:aws:bedrock:*::foundation-model/<foundation-model-id>",
]
