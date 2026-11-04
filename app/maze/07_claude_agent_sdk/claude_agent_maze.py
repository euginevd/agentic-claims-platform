"""Maze agent with the Claude Agent SDK (Claude Code's harness as a library) on Amazon Bedrock.

Run:  uv run python app/maze/07_claude_agent_sdk/claude_agent_maze.py
Needs AWS credentials (for example `aws sso login`) and MODEL_ID set to a Claude model on Bedrock.
"""

import asyncio
import os
import urllib.parse
import urllib.request
from typing import Any

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ResultMessage,
    create_sdk_mcp_server,
    query,
    tool,
)

ALLOWED_HOST = "maze.edwarddonner.com"
MAX_TURNS = 25
MAX_BUDGET_USD = 0.50
MAX_PAGE_CHARS = 3000
FETCH_TIMEOUT_SECONDS = 10

TASK = "Have a look at https://maze.edwarddonner.com and do what it says."
SYSTEM_PROMPT = (
    "You are an agent that completes tasks by using your tools, one step at a time. "
    "Only visit pages inside the maze."
)


def is_allowed(url):
    """True only for https URLs on the maze's exact host, so look-alike hosts are refused."""
    parsed = urllib.parse.urlparse(url)
    return parsed.scheme == "https" and parsed.hostname == ALLOWED_HOST


@tool(
    "read_web_page",
    "Read a page of the maze and return its text, including its links.",
    {"url": str},
)
async def read_web_page(args: dict[str, Any]) -> dict[str, Any]:
    url = args["url"]
    if not is_allowed(url):
        text = f"Error: only https://{ALLOWED_HOST} pages may be read."
        return {"content": [{"type": "text", "text": text}], "is_error": True}

    def fetch():
        # The URL is checked against the allowlist above, so urlopen can't reach other hosts.
        with urllib.request.urlopen(url, timeout=FETCH_TIMEOUT_SECONDS) as response:  # noqa: S310
            return response.read().decode("utf-8", errors="replace")[:MAX_PAGE_CHARS]

    page = await asyncio.to_thread(fetch)
    return {"content": [{"type": "text", "text": page}]}


def build_options(model_id, region="ap-southeast-2"):
    """The harness settings: our one tool, no built-in tools, caps on turns and spend."""
    maze_server = create_sdk_mcp_server(name="maze", version="1.0.0", tools=[read_web_page])
    return ClaudeAgentOptions(
        model=model_id,
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={"maze": maze_server},
        tools=[],  # no built-in tools (no Bash, no file edits, no web search)
        allowed_tools=["mcp__maze__read_web_page"],  # pre-approved, so no permission prompt
        max_turns=MAX_TURNS,
        max_budget_usd=MAX_BUDGET_USD,
        # Route the harness's model calls to Amazon Bedrock with the AWS credentials in use.
        env={"CLAUDE_CODE_USE_BEDROCK": "1", "AWS_REGION": region},
    )


async def run(model_id, region="ap-southeast-2"):
    options = build_options(model_id, region)
    async for message in query(prompt=TASK, options=options):
        if isinstance(message, ResultMessage):
            return {
                "status": message.subtype,
                "answer": message.result,
                "turns": message.num_turns,
                "costUsd": message.total_cost_usd,
            }
    return {"status": "no_result"}


def main():
    result = asyncio.run(
        run(os.environ["MODEL_ID"], os.environ.get("AWS_REGION", "ap-southeast-2"))
    )
    print(result)


if __name__ == "__main__":
    main()
