"""Single-call claims eval on Amazon Bedrock: every claim, several models, one table.

Each claim is one Converse call. Structured output comes from forcing a tool whose input
schema is the ClaimDecision model, which works the same way on every Converse model.
The answers are scored in code against the handlers' decisions, which the model never sees.

Run:  uv run python app/claims/01_eval_single_call/eval_single_call.py [--models "Claude Haiku"]
Needs AWS credentials (for example `aws sso login`) and access to the models in models.json.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # so `claims_core` imports when run as a script

import boto3  # noqa: E402
from botocore.config import Config  # noqa: E402
from botocore.exceptions import ClientError  # noqa: E402
from claims_core import scoring, store  # noqa: E402
from claims_core.models import ClaimDecision  # noqa: E402
from pydantic import ValidationError  # noqa: E402

TOOL_NAME = "record_decision"
MAX_TOKENS = 800

INSTRUCTIONS = """You are a claims handler at Tern Travel Insurance.
Decide the claim you are given using the policy wording and the claims manual below,
and the customer's policy record. Record your decision with the record_decision tool.

- approve: the wording covers the claim and the required documents are on file. Work out the
  payout with section 6 of the wording.
- decline: the wording does not cover the claim.
- refer: a required document is missing, the story and documents disagree, or the manual
  says to refer.
"""


def system_prompt():
    """Fixed for every claim, so it can be cached: the instructions, the wording and the manual."""
    return "\n\n".join(
        [INSTRUCTIONS, store.document_text("policy_wording"), store.document_text("claims_manual")]
    )


def user_prompt(claim):
    """The parts that change per claim: the policy record and the claim, as compact JSON."""
    policy = store.get_policy(claim["policy_id"])
    return f"# Policy record\n{json.dumps(policy)}\n\n# Claim\n{json.dumps(claim)}"


def tool_config():
    return {
        "tools": [
            {
                "toolSpec": {
                    "name": TOOL_NAME,
                    "description": "Record the decision on the claim.",
                    "inputSchema": {"json": ClaimDecision.model_json_schema()},
                }
            }
        ],
        # Forcing this tool makes the reply a ClaimDecision, not free text.
        "toolChoice": {"tool": {"name": TOOL_NAME}},
    }


def decide(client, model, claim):
    """One Converse call for one claim. A missing or invalid answer counts as 'none' (wrong)."""
    start = time.time()
    result = {"model": model["name"], "claim_id": claim["claim_id"], "cost": 0.0}
    try:
        response = client.converse(
            modelId=model["id"],
            system=[{"text": system_prompt()}],
            messages=[{"role": "user", "content": [{"text": user_prompt(claim)}]}],
            toolConfig=tool_config(),
            inferenceConfig={"maxTokens": MAX_TOKENS, "temperature": 0},
        )
    except ClientError as error:
        return {**result, "decision": "none", "payout": 0.0, "rationale": str(error), "seconds": 0}
    usage = response["usage"]
    result["cost"] = (
        usage["inputTokens"] * model["input_per_million_usd"]
        + usage["outputTokens"] * model["output_per_million_usd"]
    ) / 1_000_000
    result["seconds"] = round(time.time() - start, 2)
    blocks = response["output"]["message"]["content"]
    tool_input = next((b["toolUse"]["input"] for b in blocks if "toolUse" in b), None)
    try:
        answer = ClaimDecision.model_validate(tool_input)
    except ValidationError as error:
        return {**result, "decision": "none", "payout": 0.0, "rationale": str(error)}
    return {**result, **answer.model_dump()}


def load_models(names=None):
    models = json.loads((HERE / "models.json").read_text(encoding="utf-8"))["models"]
    return [m for m in models if not names or m["name"] in names]


def print_table(rows):
    columns = list(rows[0])
    print("| " + " | ".join(columns) + " |")
    print("|" + "---|" * len(columns))
    for row in rows:
        print("| " + " | ".join(str(row[c]) for c in columns) + " |")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--models", nargs="*", help="model names from models.json (default: all)")
    parser.add_argument(
        "--repeats", type=int, default=1, help="runs per model, to check it's consistent"
    )
    parser.add_argument(
        "--misses", action="store_true", help="print each wrong answer with the reason"
    )
    options = parser.parse_args()

    region = os.environ.get("AWS_REGION", "ap-southeast-2")
    client = boto3.client(
        "bedrock-runtime", region_name=region, config=Config(retries={"mode": "adaptive"})
    )
    labels = scoring.load_labels()
    claims = store.list_claims()

    rows = []
    for model in load_models(options.models):
        for run in range(1, options.repeats + 1):
            results = [decide(client, model, claim) for claim in claims]
            summary = scoring.score(results, labels)
            rows.append(
                {
                    "model": model["name"],
                    "run": run,
                    **summary,
                    **scoring.by_difficulty(results, labels),
                }
            )
            if options.misses:
                print_misses(model["name"], results, labels)
    print_table(rows)


def print_misses(name, results, labels):
    """Each wrong answer next to the handler's, with what the claim is there to test."""
    for r in results:
        label = labels[r["claim_id"]]
        if not scoring.is_right(r["decision"], r["payout"], label):
            got = f"{r['decision']} {r['payout']:.2f}"
            want = f"{label['decision']} {label['payout']:.2f}"
            print(f"- {name} {r['claim_id']}: {got}, handler {want}. Tests: {label['tests']}")


if __name__ == "__main__":
    main()
