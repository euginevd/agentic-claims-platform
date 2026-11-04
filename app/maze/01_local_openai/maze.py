"""Maze agent as a plain Python script: the OpenAI SDK, an API key in .env, no cloud.

Run:  uv run python app/maze/01_local_openai/maze.py
"""

import json
import os
import sys
import urllib.parse
import urllib.request

from dotenv import load_dotenv
from openai import OpenAI

# A small, cheap OpenAI model is enough for the maze. Override with MODEL in .env.
DEFAULT_MODEL = "gpt-6-luna"

ALLOWED_HOST = "maze.edwarddonner.com"
MAX_STEPS = 25
MAX_PAGE_CHARS = 3000
FETCH_TIMEOUT_SECONDS = 10

TASK = "Have a look at https://maze.edwarddonner.com and do what it says."
SYSTEM_PROMPT = (
    "You are an agent that completes tasks by using your tools, one step at a time. "
    "Only visit pages inside the maze."
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_web_page",
            "description": "Read a page of the maze and return its text, including its links.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "Full https URL"}},
                "required": ["url"],
            },
        },
    }
]


def read_web_page(url):
    """Fetch a maze page. Any other host or scheme is refused, so the tool can't be misused."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST:
        return f"Error: only https://{ALLOWED_HOST} pages may be read."
    # The URL is checked against the allowlist above, so urlopen can't reach other hosts.
    with urllib.request.urlopen(url, timeout=FETCH_TIMEOUT_SECONDS) as response:  # noqa: S310
        return response.read().decode("utf-8", errors="replace")[:MAX_PAGE_CHARS]


def run_tool(tool_call):
    """Run the tool the model asked for. Errors go back to the model instead of crashing."""
    try:
        if tool_call.function.name != "read_web_page":
            text = f"Error: unknown tool {tool_call.function.name}"
        else:
            text = read_web_page(**json.loads(tool_call.function.arguments))
    except Exception as error:  # noqa: BLE001 - any failure is reported to the model
        text = f"Error: {error}"
    return {"role": "tool", "tool_call_id": tool_call.id, "content": text}


def run_agent(client, model, task=TASK, max_steps=MAX_STEPS):
    """Call the model in a loop, running its tool calls, until it answers or hits the step cap."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]
    usage = {"inputTokens": 0, "outputTokens": 0}

    for step in range(1, max_steps + 1):
        response = client.chat.completions.create(model=model, messages=messages, tools=TOOLS)
        if response.usage:
            usage["inputTokens"] += response.usage.prompt_tokens
            usage["outputTokens"] += response.usage.completion_tokens
        message = response.choices[0].message
        print(f"Step {step}: {len(message.tool_calls or [])} tool call(s), model {response.model}")

        if message.tool_calls:
            messages.append(message)
            messages.extend(run_tool(tool_call) for tool_call in message.tool_calls)
        elif (message.content or "").strip():
            return {"status": "done", "answer": message.content, "steps": step, "usage": usage}
        # An empty reply (free models sometimes send one) just goes round again.

    return {"status": "step_limit", "answer": "", "steps": max_steps, "usage": usage}


def main():
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("Set OPENAI_API_KEY in a .env file (see .env.example).")
    # The client reads OPENAI_API_KEY itself, and OPENAI_BASE_URL if it's set
    # (for example to point the same code at OpenRouter or a local model).
    client = OpenAI(timeout=120, max_retries=5)
    result = run_agent(client, os.getenv("MODEL", DEFAULT_MODEL))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
