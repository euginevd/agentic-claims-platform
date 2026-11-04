# agentic-claims-platform

A production-grade agentic AI platform for travel insurance claims, built on AWS with Terraform and GitHub Actions, security first.

An agent works the claims queue, looks up the policy wording and claims manual, and decides each claim (approve, decline or refer) with its reasons. A human signs off large payouts.

## Agents

Eight numbered versions of the first agent form an agent ladder, from a hand-written loop to frameworks (Strands, LangGraph), a harness (Claude Agent SDK) and managed services, hosted on a laptop, Lambda or AgentCore Runtime. See [app/maze/README.md](app/maze/README.md) for when to use which.

## Status

Phase 1, foundation. See [docs/STATUS.md](docs/STATUS.md).

## Principles

- No long-lived credentials: GitHub OIDC to AWS, secrets in AWS Secrets Manager.
- Everything as code: Terraform for infrastructure, GitHub Actions for CI/CD.
- Security scanning on every change.
- Data stays in the AWS Sydney region (`ap-southeast-2`).

## Credits

Built on patterns from Ed Donner's course *AI FDE: The Forward Deployed Engineer & Agentic AI Architect*. All code and data here are original; the insurer and its claims are fictional.
