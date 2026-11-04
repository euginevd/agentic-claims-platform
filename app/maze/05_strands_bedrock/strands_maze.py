"""Maze agent with Strands Agents (AWS's open-source agent framework) on Amazon Bedrock.

Run:  uv run python app/maze/05_strands_bedrock/strands_maze.py
Needs AWS credentials (for example `aws sso login`) and MODEL_ID set to a Bedrock model.
"""

import os
import urllib.parse
import urllib.request

from strands import Agent, tool
from strands.models import BedrockModel

ALLOWED_HOST = "maze.edwarddonner.com"
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


@tool
def read_web_page(url: str) -> str:
    """Read a page of the maze and return its text, including its links.

    Args:
        url: The full https URL of a maze page.
    """
    if not is_allowed(url):
        return f"Error: only https://{ALLOWED_HOST} pages may be read."
    # The URL is checked against the allowlist above, so urlopen can't reach other hosts.
    with urllib.request.urlopen(url, timeout=FETCH_TIMEOUT_SECONDS) as response:  # noqa: S310
        return response.read().decode("utf-8", errors="replace")[:MAX_PAGE_CHARS]


def build_agent(model_id, region="ap-southeast-2"):
    """The whole agent: a Bedrock model, a system prompt and one tool. Strands runs the loop."""
    model = BedrockModel(model_id=model_id, region_name=region, max_tokens=4096)
    return Agent(model=model, system_prompt=SYSTEM_PROMPT, tools=[read_web_page])


def main():
    agent = build_agent(os.environ["MODEL_ID"], os.environ.get("AWS_REGION", "ap-southeast-2"))
    result = agent(TASK)
    print(result)
    print(result.metrics.get_summary()["accumulated_usage"])


if __name__ == "__main__":
    main()
