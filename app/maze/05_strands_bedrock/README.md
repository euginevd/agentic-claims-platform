# 05 · Strands Agents on Bedrock (lightweight framework)

The maze agent with **Strands Agents**, AWS's open-source agent framework. You give it a model, a system prompt and tools; Strands runs the loop. It's built for Bedrock and AgentCore, so it's the native AWS choice.

Ladder step: **lightweight framework**. Compare with [`../02_lambda_converse`](../02_lambda_converse), which writes the same loop by hand. Overview: [../README.md](../README.md).

## The code (`strands_maze.py`)

| Part | What it does |
|---|---|
| `is_allowed(url)` | Exact allowlist: `https` and host `maze.edwarddonner.com` only |
| `@tool read_web_page(url)` | Strands' decorator turns the function into a tool; the schema comes from the type hints and the docstring's `Args:` |
| `build_agent(model_id)` | `BedrockModel(model_id, region_name, max_tokens)` plus `Agent(model, system_prompt, tools)`. **That's the whole agent.** |
| `main()` | `agent(TASK)` runs the loop until the model answers; prints the answer and the token usage from `result.metrics` |

## Why choose it

- **Least code** of the framework options, and model-neutral within Bedrock.
- **AWS-native:** works directly with Bedrock (including **Bedrock Guardrails** through `guardrail_id` on the model) and is the natural code to host on AgentCore Runtime. Wrap `build_agent` in the AgentCore app from [`../04_agentcore_runtime`](../04_agentcore_runtime) to deploy it.
- **Grows with you:** conversation managers, multi-agent patterns and MCP tools are built in.

**Trade-offs:** it's AWS-led, so outside AWS LangGraph has the bigger community; and you control less of the loop than with a hand-written one (02).

## Run it

```powershell
aws sso login                         # or any AWS credentials
$env:MODEL_ID = "<Bedrock model or inference profile ID>"
uv run python app\maze\05_strands_bedrock\strands_maze.py
```

Costs a few cents in Bedrock tokens. Tests (`tests/test_maze_05_to_07_frameworks.py`) check the allowlist and that the agent has only the maze tool, with no model call.
