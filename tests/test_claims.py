"""Tests for the claims slice. No model, AWS or network calls: stubs stand in for both."""

import claim_agent
import eval_single_call
import pytest
from claims_core import rules, scoring, store
from langchain_core.messages import AIMessage

LABELS = scoring.load_labels()

# --- Data ---------------------------------------------------------------------


def test_every_claim_has_a_label_a_policy_and_a_customer():
    for claim in store.list_claims():
        assert claim["claim_id"] in LABELS
        assert store.get_policy(claim["policy_id"])["customer_id"] == claim["customer_id"]
        store.get_claim_history(claim["customer_id"])


def test_labels_obey_the_rules():
    """Every handler's decision can be recorded, so the labels and the rules agree."""
    ledger = rules.Ledger()
    for claim_id, label in LABELS.items():
        ledger.record_decision(claim_id, label["decision"], label["payout"], "s", "r")
    assert ledger.entries["CLM-0011"].status == "waiting_for_sign_off"


def test_documents_split_into_sections_and_search():
    assert store.read_section("policy_wording", 6)["title"] == "How we work out the payment"
    hits = store.search_documents("receipts")
    assert {"document": "claims_manual", "section": 4, "title": "Meals without receipts"} in hits


def test_the_agent_side_never_reaches_the_labels():
    assert "evals" not in str(store.DATA_DIR)
    assert not hasattr(claim_agent, "scoring")  # only imported inside main(), after the run
    data_files = {p.name for p in store.DATA_DIR.iterdir()}
    assert "decisions.json" not in data_files


# --- Rules --------------------------------------------------------------------


def test_one_decision_per_claim():
    ledger = rules.Ledger()
    ledger.record_decision("CLM-0001", "approve", 280, "s3", "r")
    with pytest.raises(rules.RuleViolation, match="already has a decision"):
        ledger.record_decision("CLM-0001", "decline", 0, "s3", "r")


def test_decline_and_refer_pay_nothing():
    with pytest.raises(rules.RuleViolation, match="payout of 0"):
        rules.Ledger().record_decision("CLM-0002", "decline", 50, "s2", "r")


def test_over_the_limit_waits_for_sign_off_then_pays_once():
    ledger = rules.Ledger()
    ledger.record_decision("CLM-0011", "approve", 2250, "s2", "r")
    with pytest.raises(rules.RuleViolation, match="sign-off"):
        ledger.pay("CLM-0011", 2250)
    assert ledger.sign_off("CLM-0011", "Senior handler").status == "paid"
    with pytest.raises(rules.RuleViolation, match="already been paid"):
        ledger.pay("CLM-0011", 2250)


def test_payment_must_match_the_approved_payout():
    ledger = rules.Ledger()
    ledger.record_decision("CLM-0001", "approve", 280, "s3", "r")
    with pytest.raises(rules.RuleViolation, match="must equal"):
        ledger.pay("CLM-0001", 4000)
    assert ledger.pay("CLM-0001", 280).status == "paid"


# --- Scoring ------------------------------------------------------------------


def test_score_reports_baseline_and_wrong_approvals():
    results = [
        {"claim_id": "CLM-0001", "decision": "approve", "payout": 280.0, "seconds": 1},
        {"claim_id": "CLM-0002", "decision": "approve", "payout": 1200.0, "seconds": 3},
    ]
    summary = scoring.score(results, LABELS)
    assert summary["right"] == 1
    assert summary["wrong_approvals"] == 1
    assert summary["always_approve_baseline"] == 1
    assert summary["p50_seconds"] == 2


# --- 01 single-call eval ------------------------------------------------------


class StubBedrock:
    """Replies to converse() with a forced record_decision tool call."""

    def __init__(self, tool_input):
        self.tool_input, self.requests = tool_input, []

    def converse(self, **request):
        self.requests.append(request)
        return {
            "output": {
                "message": {
                    "content": [
                        {
                            "toolUse": {
                                "toolUseId": "t1",
                                "name": "record_decision",
                                "input": self.tool_input,
                            }
                        }
                    ]
                }
            },
            "usage": {"inputTokens": 1_000_000, "outputTokens": 0},
        }


MODEL = {"name": "Stub", "id": "stub", "input_per_million_usd": 0.5, "output_per_million_usd": 2}


def test_single_call_forces_the_tool_and_parses_the_decision():
    client = StubBedrock({"rationale": "Section 3.", "decision": "approve", "payout": 280})
    result = eval_single_call.decide(client, MODEL, store.get_claim("CLM-0001"))
    assert (result["decision"], result["payout"], result["cost"]) == ("approve", 280, 0.5)
    request = client.requests[0]
    assert request["toolConfig"]["toolChoice"] == {"tool": {"name": "record_decision"}}
    # The prompt carries the claim but never the handler's answer.
    prompt = request["system"][0]["text"] + request["messages"][0]["content"][0]["text"]
    assert "CLM-0001" in prompt and LABELS["CLM-0001"]["reason"] not in prompt


def test_single_call_counts_an_invalid_answer_as_none():
    client = StubBedrock({"decision": "maybe", "payout": -5})
    assert eval_single_call.decide(client, MODEL, store.get_claim("CLM-0001"))["decision"] == "none"


# --- 02 claim agent -----------------------------------------------------------


class StubModel:
    """Plays back scripted tool calls, then a final answer, recording what it was shown."""

    def __init__(self, *calls):
        self.calls, self.seen = list(calls), []

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        self.seen.append(messages)
        if self.calls:
            name, args = self.calls.pop(0)
            return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": name}])
        return AIMessage(content="Done")


def test_agent_tools_are_bound_to_one_claim():
    tools = claim_agent.make_tools("CLM-0001", rules.Ledger())
    assert [t.name for t in tools] == [
        "get_claim",
        "get_policy",
        "get_claim_history",
        "search_documents",
        "read_section",
        "record_decision",
        "pay_claim",
    ]
    for name in ("get_claim", "get_policy", "get_claim_history"):
        assert next(t for t in tools if t.name == name).args == {}  # no id to point elsewhere


def test_agent_over_the_limit_is_refused_payment_and_waits():
    model = StubModel(
        ("get_claim", {}),
        (
            "record_decision",
            {"decision": "approve", "payout": 2250, "sections": "2, 6", "reason": "Covered."},
        ),
        ("pay_claim", {"amount": 2250}),
    )
    ledger = rules.Ledger()
    result = claim_agent.decide_claim(model, "CLM-0011", ledger)
    assert result["status"] == "waiting_for_sign_off"
    last_tool_result = model.seen[-1][-1].content
    assert last_tool_result.startswith("Refused") and "sign-off" in last_tool_result


def test_agent_injection_cannot_pay_more_than_recorded():
    model = StubModel(
        ("record_decision", {"decision": "approve", "payout": 250, "sections": "4", "reason": "r"}),
        ("pay_claim", {"amount": 4000}),
    )
    ledger = rules.Ledger()
    claim_agent.decide_claim(model, "CLM-0901", ledger)
    assert ledger.entries["CLM-0901"].status == "decided"  # the $4,000 payment was refused


def test_agent_without_a_decision_scores_as_none():
    result = claim_agent.decide_claim(StubModel(("get_claim", {})), "CLM-0001", rules.Ledger())
    assert result["decision"] == "none"
