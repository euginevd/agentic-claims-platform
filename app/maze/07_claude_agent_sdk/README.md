# 07 · Claude Agent SDK on Bedrock (batteries-included harness)

The maze agent with the **Claude Agent SDK**: Claude Code's whole harness as a Python library. It brings the loop, context management, built-in tools (files, shell, web), subagents, hooks, permissions and sessions. Here almost all of that is **switched off**, leaving one custom tool, to show how to lock a powerful harness down.

Ladder step: **batteries-included harness** (as in the course's 1.5, Lab 1). Not to be confused with **03**, which uses the plain Anthropic SDK's tool runner (a loop only, no built-in tools). Overview: [../README.md](../README.md).

## The code (`claude_agent_maze.py`)

| Part | What it does |
|---|---|
| `@tool("read_web_page", description, {"url": str})` | Defines a custom tool. The handler is `async` and returns `{"content": [{"type": "text", "text": ...}]}`; a refusal also sets `"is_error": True` |
| `create_sdk_mcp_server(name="maze", ...)` | Wraps the tool in an **in-process MCP server**: the harness talks to every tool through MCP |
| `tools=[]` | **Removes every built-in tool** (no Bash, no file edits, no web search), so only our tool exists |
| `allowed_tools=["mcp__maze__read_web_page"]` | Pre-approves our tool (its full name is `mcp__<server>__<tool>`), so it runs without a permission prompt |
| `max_turns=25`, `max_budget_usd=0.50` | Caps on steps **and on spend**, enforced by the harness |
| `env={"CLAUDE_CODE_USE_BEDROCK": "1", ...}` | Sends the model calls to **Amazon Bedrock** with your AWS credentials instead of Anthropic's API |
| `query(prompt, options)` | Runs the agent; the final `ResultMessage` carries the answer, turns and total cost |

## Why choose it

- **The most capability for the least code:** file work, shell, web, subagents, to-dos, hooks and sessions are built in. You build "Claude Code for X" agents (ops, research, document processing).
- **Controls are built in too:** permission modes, allow and deny lists, hooks before and after each tool call, budgets.

**Trade-offs:**
- **Claude only**, and a large dependency (it bundles the Claude Code runtime, about 145 MB).
- **Lock it down deliberately:** its default tools can run shell commands and edit files. In production, use `tools=[]` or a short list, a sandbox (container or AgentCore session) and explicit allow lists, as here.
- More moving parts than 05 or 06 when you only need one tool.

## Run it

```powershell
aws sso login
$env:MODEL_ID = "<Claude model or inference profile ID on Bedrock>"
uv run python app\maze\07_claude_agent_sdk\claude_agent_maze.py
```

Tests check that the options lock the harness down (no built-ins, one allowed tool, turn cap, Bedrock) and that the tool refuses other hosts, with no model call.
