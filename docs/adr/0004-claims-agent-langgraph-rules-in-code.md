# ADR 0004: Claims agent on LangGraph, with the rules in code and evals first

**Status:** accepted

## Context

The claims agent decides travel insurance claims. Some approvals pay over $1,000, and those must wait for a human. Mistakes have different costs:
- a wrong approval pays money that isn't owed
- a wrong decline harms a customer
- a wrong referral wastes a handler's time

The agent will grow to need saved state, a pause for sign-off, a queue and parallel work. We need to know it's good enough before it runs, and to choose a model on evidence.

## Decision

- **Evals first.**
  - The handlers' decisions live in `app/claims/evals/`, apart from the data. Only the scoring code reads them.
  - Each run reports decision and payout accuracy, wrong approvals, the always-approve baseline, cost and p50 latency.
  - Models are chosen as **the cheapest that reliably clears the bar**.
- **Structured output by forcing a tool** whose input schema is the Pydantic decision model. It works the same on every Bedrock Converse model.
- **LangGraph** for the agent.
  - It gives durable state (checkpointers), a pause for human approval (`interrupt`), branching and parallel work. Those are the next steps for claims.
  - It's the most common framework for stateful agents in enterprises and isn't tied to one cloud.
  - Models come from Bedrock through `ChatBedrockConverse`. Claude Haiku is the default.
- **Narrow tools bound to one claim.** No tool takes a claim, policy or customer ID, and there are no generic file or query tools. That's least privilege and data minimisation.
- **The rules are enforced in code, not in the prompt:**
  - one decision per claim
  - nothing paid on a decline or referral
  - sign-off over $1,000
  - no double or mismatched payment

  A refusal goes back to the model as a tool result.
- **Tests use a stub model and a stub Bedrock client.** CI never calls a model or AWS.

## Alternatives considered

- **Strands Agents:** less code and AWS-native (see `app/maze/05`), but its human-approval and durable-state support is less mature for a workflow like this.
- **A ready-made harness (Claude Agent SDK, Deep Agents) over a folder of files:** quick to build, but it exposes every customer's data, writes free-form output, and keeps the rules only in the prompt. It also ties us to one model (Claude Agent SDK) or adds a heavy dependency.
- **The rules in the prompt only:** a model, or a prompt injection in a claim, could break them.

## Consequences

- A little more code than a ready-made harness, in exchange for control, audit and model choice.
- The `Ledger` is in memory for now. It becomes the claims API (Lambda + DynamoDB) when deployed, with the same rules.
- Model IDs and prices in `models.json` must be checked in each account and refreshed as new models arrive.
