"""Tests for ladder steps 05 to 07. No model, AWS or network calls."""

import asyncio

import claude_agent_maze
import langgraph_maze
import pytest
import strands_maze
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

ALLOWED = "https://maze.edwarddonner.com/1"
BLOCKED = [
    "https://example.com",
    "http://maze.edwarddonner.com",
    "https://maze.edwarddonner.com.evil.io",
]


@pytest.mark.parametrize("module", [strands_maze, langgraph_maze, claude_agent_maze])
def test_allowlist_is_exact(module):
    assert module.is_allowed(ALLOWED)
    assert not any(module.is_allowed(url) for url in BLOCKED)


# --- 05 Strands ---------------------------------------------------------------


def test_strands_agent_has_only_the_maze_tool(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "ap-southeast-2")
    agent = strands_maze.build_agent("test-model")
    assert agent.tool_names == ["read_web_page"]


# --- 06 LangGraph -------------------------------------------------------------


class StubModel:
    """Asks for one tool call, then answers. Records the messages it was given."""

    def __init__(self):
        self.calls = []

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        self.calls.append(messages)
        if len(self.calls) == 1:
            return AIMessage(
                content="",
                tool_calls=[{"name": "read_web_page", "args": {"url": ALLOWED}, "id": "c1"}],
            )
        return AIMessage(content="Escaped")


@tool
def stub_read_web_page(url: str) -> str:
    """Read a maze page.

    Args:
        url: The page URL.
    """
    return "You found the exit."


stub_read_web_page.name = "read_web_page"


def test_langgraph_loops_tool_then_answers_and_saves_state():
    model = StubModel()
    app = langgraph_maze.build_graph(model, tools=[stub_read_web_page])
    config = {"configurable": {"thread_id": "t1"}}

    final = app.invoke({"messages": [("user", "go")]}, config)

    assert final["messages"][-1].content == "Escaped"
    assert len(model.calls) == 2
    # The checkpointer saved the thread: its state can be read back (and resumed).
    saved = app.get_state(config).values["messages"]
    assert [m.type for m in saved] == ["human", "ai", "tool", "ai"]


# --- 07 Claude Agent SDK ------------------------------------------------------


def test_claude_agent_options_lock_down_the_harness():
    options = claude_agent_maze.build_options("test-model")
    assert options.tools == []
    assert options.allowed_tools == ["mcp__maze__read_web_page"]
    assert options.max_turns == claude_agent_maze.MAX_TURNS
    assert options.env["CLAUDE_CODE_USE_BEDROCK"] == "1"


def test_claude_agent_tool_refuses_other_hosts():
    result = asyncio.run(claude_agent_maze.read_web_page.handler({"url": BLOCKED[2]}))
    assert result["is_error"] is True
