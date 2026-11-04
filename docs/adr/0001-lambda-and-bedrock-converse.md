# ADR 0001: The first agent runs on Lambda and calls Bedrock's Converse API directly

**Status:** accepted

## Context

The first workload is a small agent: one model, one tool, a loop of at most 25 steps, a few minutes per run.

## Decision

- Host it on **AWS Lambda** (Python 3.12, arm64), invoked through IAM only, with no public endpoint.
- Call **Amazon Bedrock's Converse API** with boto3, with no agent framework.
- Use Claude Haiku in **ap-southeast-2**, set by `MODEL_ID`.

## Consequences

- Nothing to run or patch, and no cost when idle. Reserved concurrency of 1 caps cost.
- The 15-minute Lambda limit rules it out for long agent runs; those move to AgentCore Runtime (ADR to follow).
- Converse is Bedrock-specific. A gateway (such as LiteLLM) or an adapter is needed before supporting other clouds.

## Deferred

VPC with endpoints, customer-managed KMS keys, code signing and a dead-letter queue: prod controls, recorded as Checkov skips with reasons.
