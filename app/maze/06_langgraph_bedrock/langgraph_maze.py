"""Maze agent as a LangGraph graph on Amazon Bedrock, with a checkpointer for saved state.

Run:  uv run python app/maze/06_langgraph_bedrock/langgraph_maze.py
Needs AWS credentials (for example `aws sso login`) and MODEL_ID set to a Bedrock model.
"""

import os
import urllib.parse
import urllib.request
import uuid

from langchain_aws import ChatBedrockConverse
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

ALLOWED_HOST = "maze.edwarddonner.com"
MAX_STEPS = 25
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


def build_graph(model, tools=(read_web_page,), checkpointer=None):
    """Two nodes in a loop: the model decides, the tool node acts, until no tool is asked for."""
    tools = list(tools)
    model_with_tools = model.bind_tools(tools)

    def agent(state: MessagesState):
        messages = [("system", SYSTEM_PROMPT), *state["messages"]]
        return {"messages": [model_with_tools.invoke(messages)]}

    graph = StateGraph(MessagesState)
    graph.add_node("agent", agent)
    graph.add_node("tools", ToolNode(tools))
    graph.add_edge(START, "agent")
    # After the model: go to "tools" if it asked for a tool, otherwise end.
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")
    # The checkpointer saves the state after every step, keyed by thread_id.
    return graph.compile(checkpointer=checkpointer or InMemorySaver())


def main():
    model = ChatBedrockConverse(
        model=os.environ["MODEL_ID"],
        region_name=os.environ.get("AWS_REGION", "ap-southeast-2"),
        max_tokens=4096,
    )
    app = build_graph(model)
    # A thread is one run's saved state. The same thread_id would resume it.
    config = {"configurable": {"thread_id": str(uuid.uuid4())}, "recursion_limit": 2 * MAX_STEPS}
    final = app.invoke({"messages": [("user", TASK)]}, config)
    print(final["messages"][-1].content)


if __name__ == "__main__":
    main()
