# Deploying to AWS (dev)

Everything is deployed by GitHub Actions, except the one-off tasks below, which are done in the AWS console and AWS CloudShell.

## One-off tasks (console and CloudShell)

### 1. Check Bedrock model access (console)

1. Sign in to the AWS console and switch to **Asia Pacific (Sydney) `ap-southeast-2`**.
2. Open **Amazon Bedrock → Cross-region inference** and find a **Claude Haiku** inference profile.
3. Note its **inference profile ID** and **ARN**, and the **foundation model ARNs** it routes to.

### 2. Bootstrap (CloudShell)

Run this once. It creates the state bucket, the GitHub OIDC provider and roles, and the budget alarm.

```bash
# Install Terraform in CloudShell (it isn't preinstalled)
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://rpm.releases.hashicorp.com/AmazonLinux/hashicorp.repo
sudo yum install -y terraform

git clone https://github.com/euginevd/agentic-claims-platform
cd agentic-claims-platform/infra/terraform/bootstrap
terraform init
terraform apply -var="budget_email=you@example.com"
terraform output
```

The bootstrap keeps its own state locally, and CloudShell deletes home folders after 120 days without use. Back up `terraform.tfstate` once applied (for example to the state bucket under `bootstrap/`), or simply re-import if it's ever lost.

### 3. Connect GitHub (github.com → repo → Settings)

- **Environments → New environment → `dev`:** add yourself as a required reviewer, and limit deployment branches to `main`.
- **Secrets and variables → Actions → Variables:**

| Variable | Value |
|---|---|
| `TF_STATE_BUCKET` | `state_bucket` output |
| `AWS_PLAN_ROLE_ARN` | `plan_role_arn` output |
| `AWS_APPLY_ROLE_ARN` | `apply_role_arn` output |
| `MODEL_ID` | inference profile ID from step 1 |
| `BEDROCK_MODEL_ARNS` | JSON list, e.g. `["<profile-arn>","<model-arn>"]` |

These are not secrets. No AWS keys are stored in GitHub: jobs get short-lived credentials through OIDC.

## Every change (CI/CD)

1. Open a pull request. CI runs tests and scans, and `terraform plan` appears in the job summary.
2. Merge. Merging checks the code but **doesn't deploy**.

## Spin up and tear down

- **Up:** Actions → **terraform** → Run workflow → branch `main`, action `up` → approve the `dev` deployment.
- **Down:** the same, with action `down`.
- Typical test session: up → test → down, within an hour. Idle cost is about $0 either way (see ADR 0003); tearing down keeps the account clean.

## Test the agent (CloudShell)

```bash
aws lambda invoke --function-name acp-dev-maze-agent --cli-read-timeout 310 out.json && cat out.json
aws logs tail /aws/lambda/acp-dev-maze-agent --since 15m
```

## Tear down

Remove the module from `envs/dev/main.tf` and merge, or run `terraform destroy` for `envs/dev` from CloudShell. The state bucket has `prevent_destroy` set on purpose.
