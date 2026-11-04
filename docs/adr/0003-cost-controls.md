# ADR 0003: Cost controls for dev

**Status:** accepted

## Context

Dev is spun up for a test and torn down within an hour. The target is close to $0 a month.

## Decision

- **Serverless and pay-per-use only:** Lambda and Bedrock. Nothing that bills by the hour (no NAT gateway, VPC endpoints, load balancers, databases or always-on compute).
- **No paid extras until they're needed:** no customer-managed KMS keys (about $1 a month each) and no Secrets Manager secrets (about $0.40 a month each).
- **Token limits in the agent:** pages cut to 3,000 characters, replies capped at 512 tokens, at most 25 steps.
- **A cheap model:** Claude Haiku.
- **Caps:** Lambda concurrency of 1, and 7-day log retention.
- **Deploy on demand:** merges don't deploy; a manual workflow runs `up` and `down`.
- **Budget alerts** at $2, $3, $5 and $10 of actual spend, plus a forecast alert.

## What still costs money

- **Bedrock tokens per run:** usually a few cents.
- **The state bucket:** cents a month.
- **CloudWatch log ingestion:** tiny at this volume.
- **Free:** X-Ray and Lambda are within the free tier, and GitHub Actions is free for public repos.

## Revisit for prod

KMS keys, longer log retention, a VPC with endpoints and higher concurrency all add cost, and are justified by prod requirements.
