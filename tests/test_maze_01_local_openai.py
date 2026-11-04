"""Tests for the local OpenRouter maze agent. They use a stub client: no network calls."""

import json
from types import SimpleNamespace

import maze


def tool_call(url, call_id="c1"):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name="read_web_page", arguments=json.dumps({"url": url})),
    )


def response(content=None, tool_calls=None):
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(
        model="stub",
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
        choices=[SimpleNamespace(message=message)],
    )


class StubClient:
    """Plays back scripted responses through client.chat.completions.create."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **request):
        self.requests.append(request)
        return self.responses.pop(0)


def test_refuses_lookalike_host():
    assert maze.read_web_page("https://maze.edwarddonner.com.evil.io").startswith("Error")


def test_runs_tool_then_answers(monkeypatch):
    monkeypatch.setattr(maze, "read_web_page", lambda url: "You found the exit.")
    client = StubClient(
        [response(tool_calls=[tool_call("https://maze.edwarddonner.com")]), response("Done")]
    )

    result = maze.run_agent(client, "stub-model")

    assert result["status"] == "done"
    assert result["usage"] == {"inputTokens": 20, "outputTokens": 10}
    assert client.requests[1]["messages"][3]["content"] == "You found the exit."


def test_empty_reply_is_retried(monkeypatch):
    client = StubClient([response(""), response("Done")])

    result = maze.run_agent(client, "stub-model")

    assert result == {
        "status": "done",
        "answer": "Done",
        "steps": 2,
        "usage": {"inputTokens": 20, "outputTokens": 10},
    }
