# ADR 0002: CI/CD reaches AWS through GitHub OIDC, with no stored keys

**Status:** accepted

## Decision

- GitHub Actions gets short-lived credentials through an IAM OIDC provider.
- **Plan role:** `ReadOnlyAccess` plus the state bucket, trusted for pull requests only.
- **Apply role:** can manage only resources named `acp-*`, trusted only for jobs in the GitHub `dev` environment (main branch, required reviewer).
- Terraform state lives in an encrypted, versioned, private S3 bucket with native locking.

## Consequences

- No access keys exist to leak or rotate.
- A pull request can't change AWS. Deploying needs a merge to main and an approval.
- The bootstrap (bucket, OIDC, roles, budget alerts at $2, $3, $5 and $10) is applied once by hand from CloudShell.
