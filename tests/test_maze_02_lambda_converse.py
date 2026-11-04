"""Tests for the maze agent. They use a stub model and never call Bedrock or the internet."""

import handler

USAGE = {"inputTokens": 10, "outputTokens": 5}


def tool_call_response(url, tool_use_id="t1"):
    return {
        "stopReason": "tool_use",
        "usage": USAGE,
        "output": {
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "toolUse": {
                            "toolUseId": tool_use_id,
                            "name": "read_web_page",
                            "input": {"url": url},
                        }
                    }
                ],
            }
        },
    }


def answer_response(text):
    return {
        "stopReason": "end_turn",
        "usage": USAGE,
        "output": {"message": {"role": "assistant", "content": [{"text": text}]}},
    }


class StubBedrock:
    """Plays back scripted responses and records each request."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def converse(self, **request):
        self.requests.append(request)
        return self.responses.pop(0)


def test_refuses_other_hosts():
    assert handler.read_web_page("https://example.com").startswith("Error")


def test_refuses_plain_http():
    assert handler.read_web_page("http://maze.edwarddonner.com").startswith("Error")


def test_refuses_lookalike_host():
    assert handler.read_web_page("https://maze.edwarddonner.com.evil.io").startswith("Error")


def test_runs_tool_then_answers(monkeypatch):
    monkeypatch.setattr(handler, "read_web_page", lambda url: "You found the exit.")
    client = StubBedrock(
        [tool_call_response("https://maze.edwarddonner.com"), answer_response("Done")]
    )

    result = handler.run_agent(client, "test-model")

    assert result["status"] == "done"
    assert result["answer"] == "Done"
    assert result["steps"] == 2
    assert result["usage"] == {"inputTokens": 20, "outputTokens": 10}
    tool_result = client.requests[1]["messages"][2]["content"][0]["toolResult"]
    assert tool_result["content"][0]["text"] == "You found the exit."


def test_tool_error_goes_back_to_model(monkeypatch):
    def broken(url):
        raise TimeoutError("timed out")

    monkeypatch.setattr(handler, "read_web_page", broken)
    client = StubBedrock(
        [tool_call_response("https://maze.edwarddonner.com"), answer_response("Gave up")]
    )

    handler.run_agent(client, "test-model")

    tool_result = client.requests[1]["messages"][2]["content"][0]["toolResult"]
    assert tool_result["content"][0]["text"] == "Error: timed out"


def test_stops_at_step_limit(monkeypatch):
    monkeypatch.setattr(handler, "read_web_page", lambda url: "Another corridor.")
    client = StubBedrock(
        [tool_call_response("https://maze.edwarddonner.com", f"t{i}") for i in range(3)]
    )

    result = handler.run_agent(client, "test-model", max_steps=3)

    assert result["status"] == "step_limit"
    assert len(client.requests) == 3
