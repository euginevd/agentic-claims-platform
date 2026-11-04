# Maze agent: four ways to build and host the same agent

The maze agent is built four ways, numbered from simplest to most enterprise-ready. Each does the same job: a model reads a maze of linked web pages with one tool (`read_web_page`, exact host allowlist) until it finds the exit message, capped at 25 steps. What differs is **where it runs**, **which provider serves the model**, and **who writes the agent loop**.

| # | Folder | Runs on | Model through | Agent loop | Status |
|---|---|---|---|---|---|
| 01 | [`01_local_openai`](01_local_openai) | Your laptop | **OpenAI API** (key in `.env`) | OpenAI SDK, by hand | Learning and prototyping |
| 02 | [`02_lambda_converse`](02_lambda_converse) | AWS Lambda | Amazon Bedrock | Bedrock **Converse API**, by hand | **Deployed** (Terraform) |
| 03 | [`03_lambda_claude_sdk`](03_lambda_claude_sdk) | AWS Lambda | Amazon Bedrock | **Anthropic SDK tool runner** | Reference |
| 04 | [`04_agentcore_runtime`](04_agentcore_runtime) | **AgentCore Runtime** | Amazon Bedrock | Reuses 02's loop | Reference |

Read them in order: **01** is the core idea with nothing around it; **02** moves it to AWS with production controls; **03** lets an SDK write the loop; **04** changes only the host.

## Three separate choices

**1. Where does it run?**
- **Laptop (01):** a script you run by hand.
- **Lambda (02, 03):** a function that runs for at most 15 minutes, with no state between calls.
- **AgentCore Runtime (04):** an AWS host built for agents, with long sessions, isolation per session, and Memory, Gateway, Identity and Policy services to attach.

**2. Who serves the model?**
- **OpenAI API (01):** simplest to start; an API key, and data goes to OpenAI.
- **Amazon Bedrock (02 to 04):** models run inside AWS in your chosen region (Sydney here), with IAM and no API keys. The model providers have no access to your calls.

**3. Who writes the loop?**
- **By hand (01, 02, 04):** you call the model, run tools and repeat. Full control and few dependencies.
- **SDK tool runner (03):** you write the tool functions; the Anthropic SDK builds the tool schemas and runs the loop. Less code, but specific to Claude and a beta helper.

The choices are independent. 04 shows this by wrapping 02's loop in an AgentCore app with about 20 lines.

## How they differ

| | 01 local OpenAI | 02 Lambda Converse | 03 Lambda Claude SDK | 04 AgentCore |
|---|---|---|---|---|
| **Entry point** | `python maze.py` | `lambda_handler` | `lambda_handler` | `@app.entrypoint invoke` |
| **Libraries** | `openai`, `python-dotenv` | `boto3` (built into Lambda) | `anthropic` (bundled) | `bedrock-agentcore`, `boto3` (packaged) |
| **Credentials** | API key in `.env` | IAM role | IAM role | IAM role |
| **Tool schema** | JSON by hand | JSON by hand | From the function's type hints and docstring | JSON by hand (reused) |
| **Models** | OpenAI (or any OpenAI-compatible API) | Any Bedrock model | Claude only | Any Bedrock model |
| **Data residency** | OpenAI's API | AWS Sydney | AWS Sydney | AWS Sydney |
| **API maturity** | GA | GA | Tool runner is beta | Runtime GA, newer service |
| **Maximum run** | As long as you like | 15 minutes | 15 minutes | Long sessions (hours) |
| **Sessions, memory** | None | Build yourself | Build yourself | Built in or attachable |
| **Deployment** | None | Terraform + CI/CD | Terraform + package build | AgentCore CLI or Terraform |
| **Cost** | OpenAI tokens | Bedrock tokens; Lambda free tier | Bedrock tokens; Lambda free tier | Bedrock tokens; Runtime per use; KMS key about $1 a month if the CLI creates one |

## When to use which

**01 (local, OpenAI):** learning, quick experiments, comparing models, demos. Never production: a key on a laptop, no audit, and data leaves your cloud.

**02 (Lambda + Converse):** small, short, stateless agents in production.
- one or a few tools, runs well under 15 minutes, nothing to remember between calls
- fewest dependencies, and model-neutral within Bedrock
- examples: classify and route a document, extract fields from a claim, a nightly check

**03 (Lambda + Claude SDK):** production agents with many tools, Claude only.
- writing and maintaining JSON schemas for 10+ tools becomes the main cost
- you accept a beta helper (pin the SDK version) and bundling a dependency
- example: a claims triage agent calling policy, customer and payment tools

**04 (AgentCore Runtime):** long-running or conversational agents.
- runs longer than 15 minutes, or multi-turn sessions (a handler chatting with a Copilot)
- needs memory, human approval with resume, many tools through a gateway, or per-user identity
- examples: working a whole claims queue, the handler Copilot, any agent users talk to

## In an enterprise

| Concern | 01 local | 02 and 03 Lambda | 04 AgentCore |
|---|---|---|---|
| **Security review** | Not acceptable for production | Familiar to every AWS security team | Newer service; more questions, but agent-specific controls |
| **Credentials** | Long-lived key in a file | IAM role, no keys | IAM role; **AgentCore Identity** for third-party credentials |
| **Isolation** | Your laptop | Per invocation, shared warm containers | **Per session** |
| **Access to systems** | Whatever your laptop can reach | IAM per function, integrations in code | Gateway with central auth and **Cedar policies** on tool calls |
| **Audit and observability** | Console output | CloudWatch logs and X-Ray | Agent traces built in, plus logs |
| **Data residency** | The provider's region | Your region (Sydney) | Your region; check the service and model are offered there |
| **Infrastructure as code** | None | Very mature in Terraform | Terraform resources exist (`aws_bedrockagentcore_*`) but are newer |
| **Lock-in** | Low (OpenAI-compatible APIs) | Low (Converse works with any Bedrock model) | AgentCore wrapper and services; keep agent logic separate, as here |

**Typical path:** prototype locally (01), pilot on Lambda (02 or 03, fast to approve and cheap), and move to AgentCore (04) when the agent needs sessions, memory, a gateway or long runs. Keeping the agent logic separate from the hosting wrapper keeps each move small.

## In this repo

- **Deployed:** 02 on Lambda ([ADR 0001](../../docs/adr/0001-lambda-and-bedrock-converse.md)).
- **Next:** the claims agent and the handler Copilot on AgentCore Runtime (decision to be recorded as an ADR).
- Each folder's README explains its code.
