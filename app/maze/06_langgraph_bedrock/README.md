# 06 · LangGraph on Bedrock (framework with durable state)

The maze agent as a **LangGraph** graph: steps are **nodes**, the flow between them is **edges**, and a **checkpointer** saves the state after every step. LangGraph is the framework most often named in AI engineering job ads, and it's what the course uses for durable state, human approval and agent teams (2.3, 2.4).

Ladder step: **framework with durable state**. Overview: [../README.md](../README.md).

## The graph

```
START → agent ──(asked for a tool?)── yes → tools ─┐
          ▲                                         │
          └─────────────────────────────────────────┘
                  └── no → END
```

## The code (`langgraph_maze.py`)

| Part | What it does |
|---|---|
| `@tool read_web_page(url)` | LangChain's tool decorator, with the exact allowlist |
| `MessagesState` | The graph's **state**: the list of messages, which every node reads and appends to |
| `agent` node | Calls the model (with tools bound) on the system prompt plus the state's messages |
| `tools` node | `ToolNode` runs whatever tool calls the model made and appends the results |
| `tools_condition` | The **conditional edge**: go to `tools` if the model asked for one, otherwise end |
| `InMemorySaver` | The **checkpointer**: saves the state after every step, keyed by `thread_id` |
| `recursion_limit` | Caps the number of steps (two graph steps per maze step), so it can't loop for ever |
| `ChatBedrockConverse` | LangChain's Bedrock chat model (Converse API), with IAM credentials |

## Why choose it

- **Durable state:** with a database checkpointer (for example Postgres) in place of `InMemorySaver`, a run survives crashes and can be **resumed** from its `thread_id`.
- **Human in the loop:** a node can **pause** the graph (an interrupt) until a person approves, for example a payout over $1,000, then resume. This is what the course builds in 2.3.
- **Explicit control flow:** branches, retries and multi-agent teams are drawn as a graph you can read, test and review.
- **Portable:** runs on Lambda, AgentCore, containers or a laptop, with models from any provider.

**Trade-offs:** more concepts to learn than Strands (state, nodes, edges, checkpointers), and more code for a simple agent.

## Run it

```powershell
aws sso login
$env:MODEL_ID = "<Bedrock model or inference profile ID>"
uv run python app\maze\06_langgraph_bedrock\langgraph_maze.py
```

The test runs the graph with a **stub model**: it asks for one tool call, then answers. It checks that the checkpointer saved the whole thread (`human → ai → tool → ai`), which is the state you'd resume from.
