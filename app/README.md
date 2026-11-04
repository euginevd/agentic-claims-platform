# Agents: three ways to build and host the same agent

The maze agent is built three ways. Each does the same job: Claude reads a maze of linked web pages with one tool (`read_web_page`, exact host allowlist) until it finds the exit message, capped at 25 steps. What differs is **who writes the agent loop** and **where the agent runs**.

| Folder | Hosted on | Agent loop | Status |
|---|---|---|---|
| [`maze_agent`](maze_agent) | AWS Lambda | Bedrock **Converse API**, loop written by hand | **Deployed** (Terraform) |
| [`maze_agent_sdk`](maze_agent_sdk) | AWS Lambda | **Anthropic SDK tool runner** (the SDK runs the loop) | Reference |
| [`maze_agent_core`](maze_agent_core) | **AgentCore Runtime** | Reuses `maze_agent`'s loop unchanged | Reference |

## Two separate choices

**1. Who writes the loop?**
- **By hand (Converse):** you call the model, run tools and repeat. Full control, no extra library, works with any Bedrock model.
- **SDK tool runner:** you write the tool functions; the Anthropic SDK builds the tool schemas and runs the loop. Less code, but specific to Claude and a beta helper.

**2. Where does it run?**
- **Lambda:** a function that runs for at most 15 minutes, with no state between calls.
- **AgentCore Runtime:** an AWS host built for agents, with long sessions, isolation per session, and Memory, Gateway, Identity and Policy services to attach.

The two choices are independent: any loop can run on either host. `maze_agent_core` shows this by wrapping `maze_agent`'s loop in an AgentCore app with about 20 lines.

## How they differ

| | `maze_agent` | `maze_agent_sdk` | `maze_agent_core` |
|---|---|---|---|
| **Entry point** | `lambda_handler` | `lambda_handler` | `@app.entrypoint invoke` |
| **Libraries** | `boto3` (built into Lambda) | `anthropic` (bundled) | `bedrock-agentcore`, `boto3` (packaged) |
| **Tool schema** | JSON by hand | From the function's type hints and docstring | JSON by hand (reused) |
| **Models** | Any Bedrock model (Claude, Nova, Llama, Mistral) | Claude only | Any Bedrock model |
| **API maturity** | GA | Tool runner is beta | Runtime GA, newer service |
| **Maximum run** | 15 minutes | 15 minutes | Long sessions (hours) |
| **Sessions, memory** | Build yourself | Build yourself | Built in or attachable |
| **Tool access across systems** | Code each integration | Code each integration | AgentCore Gateway (APIs, Lambda, MCP as tools) |
| **Moving parts** | Function, role, log group | Function, role, log group, package build | Runtime, endpoint, role, package build |
| **Idle cost** | $0 | $0 | About $0 (consumption-based) |
| **Free tier** | Lambda free tier | Lambda free tier | No Lambda free tier; KMS key about $1 a month if the AgentCore CLI creates one |

## When to use which

**Use `maze_agent` (Lambda + Converse)** for small, short, stateless agents:
- one or a few tools, runs well under 15 minutes, no conversation to remember
- you want the fewest dependencies and to stay model-neutral within Bedrock
- examples: classify and route a document, extract fields from a claim, a nightly check

**Use `maze_agent_sdk` (Lambda + tool runner)** when the agent has many tools and is Claude-only:
- writing and maintaining JSON schemas for 10+ tools becomes the main cost
- you accept a beta helper (pin the SDK version) and bundling a dependency
- examples: a claims triage agent calling policy, customer and payment tools

**Use `maze_agent_core` (AgentCore Runtime)** for long-running or conversational agents:
- runs longer than 15 minutes, or multi-turn sessions (a handler chatting with a Copilot)
- needs memory, human approval with resume, many tools through a gateway, or per-user identity
- examples: working a whole claims queue, the handler Copilot, any agent users talk to

## In an enterprise

| Concern | Lambda (`maze_agent`, `maze_agent_sdk`) | AgentCore Runtime (`maze_agent_core`) |
|---|---|---|
| **Security review** | Familiar to every AWS security team; well-known controls | Newer service; expect more questions, though it adds agent-specific controls |
| **Isolation** | Per invocation, shared warm containers | **Per session**, so one user's agent can't see another's |
| **Access to systems** | IAM role per function, integrations in code | Gateway with central auth and **Cedar policies** on tool calls |
| **Credentials to third parties** | Secrets Manager, code fetches them | **AgentCore Identity** holds and brokers them |
| **Audit and observability** | CloudWatch logs and X-Ray, you add agent detail | Agent traces built in, plus your logs |
| **Data residency** | Region you choose (Sydney here) | Region you choose; check the service and model are offered there |
| **Infrastructure as code** | Very mature in Terraform | Terraform resources exist (`aws_bedrockagentcore_*`) but are newer |
| **Lock-in** | Low; Converse works with any Bedrock model | AgentCore-specific wrapper and services; keep agent logic separate (as here) |
| **Operations** | Nothing to run; very mature | Nothing to run; newer, so watch release notes |

**Typical path in an enterprise:** start on Lambda for a pilot (fast to approve, cheap), and move to AgentCore when the agent needs sessions, memory, a gateway or long runs. Keep the agent logic separate from the hosting wrapper so the move is small, as `maze_agent_core` shows.

## In this repo

- **Now:** `maze_agent` on Lambda is deployed ([ADR 0001](../docs/adr/0001-lambda-and-bedrock-converse.md)).
- **Next:** the claims agent and the handler Copilot move to AgentCore Runtime (decision to be recorded as an ADR).
- Each folder's README explains its code line by line.
