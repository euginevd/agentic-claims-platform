"""Maze agent on Lambda: Claude on Amazon Bedrock with the Anthropic SDK's tool runner."""

import json
import logging
import os
import urllib.parse
import urllib.request

from anthropic import AnthropicBedrockMantle, beta_tool

ALLOWED_HOST = "maze.edwarddonner.com"
MAX_STEPS = 25
# Cost controls: every step resends the whole history, so keep pages and replies short.
MAX_PAGE_CHARS = 3000
MAX_OUTPUT_TOKENS = 4096
FETCH_TIMEOUT_SECONDS = 10

TASK = "Have a look at https://maze.edwarddonner.com and do what it says."
SYSTEM_PROMPT = (
    "You are an agent that completes tasks by using your tools, one step at a time. "
    "Only visit pages inside the maze."
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Created once per Lambda container and reused across invocations.
# It signs requests with the function's IAM role, so there is no API key.
client = AnthropicBedrockMantle(aws_region=os.environ.get("AWS_REGION", "ap-southeast-2"))


@beta_tool
def read_web_page(url: str) -> str:
    """Read a page of the maze and return its text, including its links.

    Args:
        url: The full https URL of a maze page.
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST:
        return f"Error: only https://{ALLOWED_HOST} pages may be read."
    # The URL is checked against the allowlist above, so urlopen can't reach other hosts.
    with urllib.request.urlopen(url, timeout=FETCH_TIMEOUT_SECONDS) as response:  # noqa: S310
        return response.read().decode("utf-8", errors="replace")[:MAX_PAGE_CHARS]


def lambda_handler(event, context):
    """Lambda entry point. The event is ignored: the task is fixed, so callers can't change it."""
    runner = client.beta.messages.tool_runner(
        model=os.environ["MODEL_ID"],
        max_tokens=MAX_OUTPUT_TOKENS,
        max_iterations=MAX_STEPS,
        system=SYSTEM_PROMPT,
        tools=[read_web_page],
        messages=[{"role": "user", "content": TASK}],
    )
    # Each iteration is one model call; the SDK runs the tools in between.
    usage = {"inputTokens": 0, "outputTokens": 0}
    steps = 0
    final = None
    for message in runner:
        steps += 1
        usage["inputTokens"] += message.usage.input_tokens
        usage["outputTokens"] += message.usage.output_tokens
        logger.info(
            json.dumps({"event": "step", "step": steps, "stop_reason": message.stop_reason})
        )
        final = message

    # Still asking for a tool after the last iteration means the step cap stopped it.
    status = {"end_turn": "done", "tool_use": "step_limit"}.get(
        final.stop_reason, final.stop_reason
    )
    answer = "".join(block.text for block in final.content if block.type == "text")
    logger.info(json.dumps({"event": "finished", "status": status, "steps": steps, **usage}))
    return {"status": status, "answer": answer, "steps": steps, "usage": usage}
