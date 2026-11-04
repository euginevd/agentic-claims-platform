"""Scoring against the handlers' decisions. Only the eval side imports this; the agents never do."""

import json
import statistics
from pathlib import Path

LABELS_FILE = Path(__file__).resolve().parents[1] / "evals" / "decisions.json"
PAYOUT_TOLERANCE = 1.0


def load_labels():
    return {row["claim_id"]: row for row in json.loads(LABELS_FILE.read_text(encoding="utf-8"))}


def is_right(decision, payout, label):
    """The decision matches and the payout is within a dollar."""
    return decision == label["decision"] and abs(payout - label["payout"]) <= PAYOUT_TOLERANCE


def score(results, labels):
    """Summarise a run. Each result has claim_id, decision, payout, and maybe cost and seconds.

    Reports the always-approve baseline next to the score, and counts wrong approvals apart,
    because paying out money the policy doesn't owe is the costliest mistake.
    """
    n = len(results)
    decision_right = sum(r["decision"] == labels[r["claim_id"]]["decision"] for r in results)
    right = sum(is_right(r["decision"], r["payout"], labels[r["claim_id"]]) for r in results)
    wrong_approvals = sum(
        r["decision"] == "approve" and labels[r["claim_id"]]["decision"] != "approve"
        for r in results
    )
    baseline = sum(labels[r["claim_id"]]["decision"] == "approve" for r in results)
    seconds = [r["seconds"] for r in results if "seconds" in r]
    return {
        "claims": n,
        "decision_right": decision_right,
        "right": right,
        "wrong_approvals": wrong_approvals,
        "always_approve_baseline": baseline,
        "cost_usd": round(sum(r.get("cost", 0.0) for r in results), 5),
        "p50_seconds": round(statistics.median(seconds), 2) if seconds else None,
    }


def by_difficulty(results, labels):
    """How many are right at each difficulty: routine, hard, manual, security."""
    counts = {}
    for r in results:
        label = labels[r["claim_id"]]
        got, total = counts.get(label["difficulty"], (0, 0))
        counts[label["difficulty"]] = (got + is_right(r["decision"], r["payout"], label), total + 1)
    return {k: f"{got}/{total}" for k, (got, total) in counts.items()}
