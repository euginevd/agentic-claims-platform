# Maze agent: the agent ladder, one agent built eight ways

The same agent is built eight ways, from "write everything yourself" to "the provider runs it for you". Each does the same job: a model reads a maze of linked web pages with one tool (`read_web_page`, exact host allowlist) until it finds the exit message, with a step cap.

## The ladder

| # | Folder | Ladder step | Runs on | Model through | Status |
|---|---|---|---|---|---|
| 01 | [`01_local_openai`](01_local_openai) | Loop by hand | Laptop | OpenAI API (key in `.env`) | Learning |
| 02 | [`02_lambda_converse`](02_lambda_converse) | Loop by hand | AWS Lambda | Bedrock (Converse) | **Deployed** |
| 03 | [`03_lambda_claude_sdk`](03_lambda_claude_sdk) | SDK helper loop | AWS Lambda | Bedrock (Anthropic SDK tool runner) | Reference |
| 04 | [`04_agentcore_runtime`](04_agentcore_runtime) | Loop by hand, agent host | **AgentCore Runtime** | Bedrock | Reference |
| 05 | [`05_strands_bedrock`](05_strands_bedrock) | Lightweight framework | Laptop or AWS | Bedrock (Strands) | Reference |
| 06 | [`06_langgraph_bedrock`](06_langgraph_bedrock) | Framework with durable state | Laptop or AWS | Bedrock (LangGraph) | Reference |
| 07 | [`07_claude_agent_sdk`](07_claude_agent_sdk) | Batteries-included harness | Laptop or AWS | Bedrock (Claude Agent SDK) | Reference |
| 08 | [`08_managed_agents`](08_managed_agents) | Fully managed service | Provider | Provider | Explained, no code |

```
build more ─────────────────────────────────────────────────────────────── buy more
loop by hand → SDK helper → lightweight framework → durable-state framework → harness → managed
  01, 02, 04      03              05                      06                   07          08
```

Moving right, you write and maintain less, get more built in, and control less.

## Two separate questions

**1. How is the agent built?** (the ladder above)

| Step | What you write | What you get for free | Examples |
|---|---|---|---|
| Loop by hand | The loop, tool schemas, retries | Nothing | 01, 02 |
| SDK helper | Tool functions | The loop, schemas from type hints | 03 |
| Lightweight framework | Model, prompt, tools | The loop, tool handling, conversation management | 05 (Strands), LangChain `create_agent` |
| Durable-state framework | A graph of steps | Saved state, resume, pause for human approval, branching, teams | 06 (LangGraph) |
| Batteries-included harness | Options and custom tools | Built-in file, shell and web tools, subagents, hooks, permissions, sessions | 07 (Claude Agent SDK), Deep Agents |
| Managed service | Configuration | The loop **and** the environment it runs in | 08 (Managed Agents, Bedrock Agents) |

**2. Where does it run?** Independent of how it's built: **laptop** (01) → **Lambda** (02, 03: up to 15 minutes, stateless) → **AgentCore Runtime** (04: long sessions, isolation, Memory, Gateway, Identity, Policy). 05 to 07 run on a laptop as written and can be hosted on either, for example by wrapping them in 04's AgentCore app.

## When to use which

| Use | When | Avoid when |
|---|---|---|
| **01** local, OpenAI | Learning, quick experiments, comparing models | Anything with real data or users |
| **02** Lambda + Converse | Small, short, stateless production agents; fewest dependencies | Long runs, conversations, many tools |
| **03** Lambda + tool runner | Claude-only agents with many tools | You need model choice or a GA-only stack |
| **04** AgentCore Runtime | Long-running or conversational agents; per-session isolation | A tiny one-shot task (Lambda is simpler) |
| **05** Strands | Most AWS agents: little code, model-neutral, Guardrails, AgentCore-native | You need explicit multi-step control flow |
| **06** LangGraph | Workflows that must **resume**, **pause for approval**, branch or use agent teams; claims processing | A simple one-tool agent (more concepts than it needs) |
| **07** Claude Agent SDK | "Claude Code for X": agents that work with files, shell, documents and subagents | Strict model choice, or a small footprint (it's large and Claude-only) |
| **08** managed service | Fastest start when the provider's sandbox and tools fit, and its data terms are acceptable | Data must stay in your own account and region |

## In an enterprise

| Concern | 01 local | 02, 03 Lambda | 04 to 07 in your AWS account | 08 managed |
|---|---|---|---|---|
| **Credentials** | Key in a file | IAM role | IAM role (AgentCore Identity on 04) | Provider account and keys |
| **Data residency** | Provider's region | Sydney | Sydney | Provider's platform and regions |
| **Control and audit** | None | Full, in code | Full, in code; framework adds structure | Least; behaviour lives in the provider's configuration |
| **Security review** | Not for production | Familiar | Familiar host; framework is a dependency to review | Vendor assessment |
| **Lock-in** | Low | Low | Framework-level (moderate); keep logic separate | Highest |
| **Effort to build** | Lowest | Low | Medium | Lowest for supported jobs |

**Typical path:** prototype locally (01) → pick a framework (05 for most AWS work, 06 when the process needs state and approvals) → pilot on Lambda (02) → run long or conversational agents on AgentCore (04). Use a harness (07) when the job is file- and tool-heavy, and a managed service (08) when speed matters more than control and the data terms allow it.

## In this repo

- **Deployed:** 02 on Lambda ([ADR 0001](../../docs/adr/0001-lambda-and-bedrock-converse.md)).
- **Next:** the claims agent, likely LangGraph (06) for durable state and the $1,000 approval, hosted on AgentCore (04). To be recorded as an ADR.
- Each folder's README explains its code. Tests use stubs, so CI never calls a model or AWS.
