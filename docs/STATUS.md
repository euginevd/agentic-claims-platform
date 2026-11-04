# Status

## Phase 1: foundation

- [x] Repo, README, AGENTS.md, SECURITY.md
- [x] GitHub security settings and protected `main`
- [x] Secret scanning (gitleaks), dependency scanning (Trivy) and Dependabot
- [x] CI: ruff (lint, security rules, formatting) and pytest with a stub model
- [x] Terraform: bootstrap (state bucket, GitHub OIDC, plan and apply roles, budget), `lambda-agent` module, `dev` environment
- [x] Terraform CI: fmt, validate, tflint, Checkov, plan on PR, apply on merge through the `dev` environment
- [x] Maze agent: Lambda + Bedrock Converse, allowlisted tool, step cap, structured logs
- [x] Maze agent ladder: the same agent built eight ways (`app/maze`)
- [x] Claims: invented data and labels, single-call eval across Bedrock models, LangGraph claim agent with narrow tools and rules in code (`app/claims`, ADR 0004)
- [ ] Claims: first real eval run on Bedrock, and the model choice recorded
- [ ] One-off AWS set-up (bootstrap from CloudShell, GitHub variables): see `docs/DEPLOY.md`
- [ ] First deployment and test run
