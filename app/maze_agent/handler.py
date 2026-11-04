"""Maze agent: an LLM with one tool in a loop, on AWS Lambda and Amazon Bedrock."""

import json
import logging
import os
import urllib.parse
import urllib.request

import boto3

ALLOWED_HOST = "maze.edwarddonner.com"
MAX_STEPS = 25
MAX_PAGE_CHARS = 5000
FETCH_TIMEOUT_SECONDS = 10

TASK = "Have a look at https://maze.edwarddonner.com and do what it says."
SYSTEM_PROMPT = (
    "You are an agent that completes tasks by using your tools, one step at a time. "
    "Only visit pages inside the maze."
)

TOOL_CONFIG = {
    "tools": [
        {
            "toolSpec": {
                "name": "read_web_page",
                "description": "Read a page of the maze and return its text, including its links.",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {"url": {"type": "string", "description": "Full https URL"}},
                        "required": ["url"],
                    }
                },
            }
        }
    ]
}

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def log(event, **fields):
    """Write one structured JSON log line, which CloudWatch Logs Insights can query."""
    logger.info(json.dumps({"event": event, **fields}))


def read_web_page(url):
    """Fetch a maze page. Any other host or scheme is refused, so the tool can't be misused."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST:
        return f"Error: only https://{ALLOWED_HOST} pages may be read."
    # The URL is checked against the allowlist above, so urlopen can't reach other hosts.
    with urllib.request.urlopen(url, timeout=FETCH_TIMEOUT_SECONDS) as response:  # noqa: S310
        return response.read().decode("utf-8", errors="replace")[:MAX_PAGE_CHARS]


def run_tool(tool_use):
    """Run the tool the model asked for. Errors go back to the model instead of crashing."""
    try:
        if tool_use["name"] != "read_web_page":
            text = f"Error: unknown tool {tool_use['name']}"
        else:
            text = read_web_page(**tool_use["input"])
    except Exception as error:  # noqa: BLE001 - any failure is reported to the model
        text = f"Error: {error}"
    return {"toolResult": {"toolUseId": tool_use["toolUseId"], "content": [{"text": text}]}}


def run_agent(client, model_id, task=TASK, max_steps=MAX_STEPS):
    """Call the model in a loop, running its tool calls, until it answers or hits the step cap."""
    messages = [{"role": "user", "content": [{"text": task}]}]
    usage = {"inputTokens": 0, "outputTokens": 0}

    for step in range(1, max_steps + 1):
        response = client.converse(
            modelId=model_id,
            system=[{"text": SYSTEM_PROMPT}],
            messages=messages,
            toolConfig=TOOL_CONFIG,
        )
        for key in usage:
            usage[key] += response["usage"][key]
        message = response["output"]["message"]
        messages.append(message)

        tool_uses = [block["toolUse"] for block in message["content"] if "toolUse" in block]
        log("step", step=step, stop_reason=response["stopReason"], tools=len(tool_uses))

        if response["stopReason"] != "tool_use":
            answer = "".join(block.get("text", "") for block in message["content"])
            return {"status": "done", "answer": answer, "steps": step, "usage": usage}

        messages.append({"role": "user", "content": [run_tool(tool_use) for tool_use in tool_uses]})

    return {"status": "step_limit", "answer": "", "steps": max_steps, "usage": usage}


def lambda_handler(event, context):
    """Lambda entry point. The event is ignored: the task is fixed, so callers can't change it."""
    result = run_agent(boto3.client("bedrock-runtime"), os.environ["MODEL_ID"])
    log("finished", status=result["status"], steps=result["steps"], **result["usage"])
    return result
