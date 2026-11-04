# An agent on AWS Lambda that calls one Bedrock model, with least-privilege IAM.

terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
    archive = {
      source = "hashicorp/archive"
    }
  }
}

data "archive_file" "code" {
  type        = "zip"
  source_dir  = var.source_dir
  output_path = "${path.root}/.build/${var.name}.zip"
  excludes    = ["__pycache__"]
}

data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "agent" {
  name               = var.name
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

resource "aws_cloudwatch_log_group" "agent" {
  #checkov:skip=CKV_AWS_158:Default CloudWatch encryption is enough for dev; customer KMS key for prod
  #checkov:skip=CKV_AWS_338:30-day retention for dev; extend to meet the records policy for prod
  name              = "/aws/lambda/${var.name}"
  retention_in_days = var.log_retention_days
}

data "aws_iam_policy_document" "agent" {
  statement {
    sid       = "InvokeOneModel"
    actions   = ["bedrock:InvokeModel"]
    resources = var.bedrock_model_arns
  }
  statement {
    sid       = "WriteOwnLogs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.agent.arn}:*"]
  }
  statement {
    sid       = "Tracing"
    actions   = ["xray:PutTraceSegments", "xray:PutTelemetryRecords"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "agent" {
  name   = "agent"
  role   = aws_iam_role.agent.id
  policy = data.aws_iam_policy_document.agent.json
}

resource "aws_lambda_function" "agent" {
  #checkov:skip=CKV_AWS_117:No VPC, because the agent only calls Bedrock and one allowlisted site
  #checkov:skip=CKV_AWS_116:No dead-letter queue, because the function is invoked synchronously
  #checkov:skip=CKV_AWS_272:Code signing is a prod control; artifacts are built in CI
  #checkov:skip=CKV_AWS_173:The only environment variable is a model ID, which isn't secret
  function_name                  = var.name
  role                           = aws_iam_role.agent.arn
  runtime                        = "python3.12"
  architectures                  = ["arm64"]
  handler                        = "handler.lambda_handler"
  filename                       = data.archive_file.code.output_path
  source_code_hash               = data.archive_file.code.output_base64sha256
  timeout                        = var.timeout_seconds
  memory_size                    = 256
  reserved_concurrent_executions = var.max_concurrency

  environment {
    variables = {
      MODEL_ID = var.model_id
    }
  }

  tracing_config {
    mode = "Active"
  }

  depends_on = [aws_cloudwatch_log_group.agent, aws_iam_role_policy.agent]
}
