# 08 · Fully managed agent services (no code here)

The top of the ladder: **the provider runs the agent loop and its environment for you**. You configure an agent (model, instructions, tools) and send it work; there's no loop, harness or host of your own.

There's **no code in this folder on purpose**. The managed services below are configured more than coded, and the main one from Anthropic doesn't run inside AWS, so it doesn't fit this repo's Sydney data-residency rule. This page explains the options and when they fit.

Overview: [../README.md](../README.md).

## The options

| Service | Who runs it | What you get | Fit for this repo |
|---|---|---|---|
| **Claude Managed Agents** (Anthropic, beta) | Anthropic | Anthropic runs the loop and a sandbox per session (bash, files, code), with Skills, MCP, memory, schedules and multi-agent workflows | **No:** runs on Anthropic's platform, not in our AWS account in Sydney, and isn't offered on Amazon Bedrock |
| **Amazon Bedrock Agents** | AWS | Agents configured in the Bedrock console or API: **action groups** (tools as Lambda functions or OpenAPI), **knowledge bases** (managed RAG), guardrails | Possible, in-region. AWS's newer direction for custom agents is AgentCore (04) |
| **AgentCore Runtime + services** | AWS hosts, you write the agent | Hosting, sessions, Gateway, Memory, Identity, Policy (see 04) | **Yes:** the path this repo takes for long-running agents |

## When a fully managed service is the right choice

- You want an agent working **quickly** with the least engineering, and the provider's tools and sandbox cover the job.
- The work fits the service's model: for example **scheduled or long-running jobs in a sandbox** (Managed Agents), or **tool calls plus managed RAG** over company documents (Bedrock Agents).
- The client accepts where the service runs and its data terms.

## When it isn't

- **Data residency and compliance** require everything in your own cloud account and region (common in government, IRAP and regulated insurers).
- You need **full control** of the loop, state, tests and evals, or to change models freely.
- You need to **review and version everything as code** (Terraform, pull requests). Managed services can be scripted, but less of the behaviour lives in your repo.

## Where this sits on the ladder

```
build more ───────────────────────────────────────────────────────── buy more
01/02 loop by hand → 03 SDK helper → 05 Strands → 06 LangGraph → 07 Claude Agent SDK → 08 managed service
```

The further right, the less you build and maintain, and the less you control. Most enterprise agents land in the middle: a framework (05 or 06) or a harness (07), hosted in your own account (Lambda or AgentCore).
