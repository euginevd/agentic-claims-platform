# agentic-claims-platform

Instructions for coding agents. Keep this file short.

## Rules

- Never commit secrets, `.env` files, AWS account IDs or `*.tfvars`.
- Every change goes through a pull request and must pass CI and the security scans.
- Keep `docs/STATUS.md` up to date with what is built.
- Record significant decisions as ADRs in `docs/adr/`.
- Ask before creating or changing anything in AWS.

## Docs

- `docs/STATUS.md`: what is built and what is next.
- `docs/DEPLOY.md`: one-off AWS set-up and how CI/CD deploys.
- `docs/adr/`: architecture decisions.
- `SECURITY.md`: how to report a vulnerability.

## Checks

- `uv run ruff check . && uv run ruff format --check . && uv run pytest -q`
- `terraform fmt -check -recursive infra`
- Tests never call a model or AWS; they use a stub.
