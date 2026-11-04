"""Tests for the AgentCore wrapper. The agent loop is stubbed: no AWS or network calls."""

import main
from bedrock_agentcore.runtime import RequestContext


def test_invoke_runs_the_agent_and_returns_its_result(monkeypatch):
    monkeypatch.setenv("MODEL_ID", "test-model")
    expected = {
        "status": "done",
        "answer": "Escaped",
        "steps": 3,
        "usage": {"inputTokens": 30, "outputTokens": 15},
    }
    calls = []

    def stub_run_agent(client, model_id):
        calls.append(model_id)
        return expected

    monkeypatch.setattr(main, "run_agent", stub_run_agent)

    result = main.invoke({"ignored": "payload"}, RequestContext(session_id="session-1"))

    assert result == expected
    assert calls == ["test-model"]
