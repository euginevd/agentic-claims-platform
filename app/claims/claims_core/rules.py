"""The business rules, enforced in code rather than in the prompt.

Whatever the model says, these hold: one decision per claim, no payout on a decline or a
referral, an approval over the limit waits for a handler's sign-off, and no claim is paid
twice or for a different amount. In production this is the claims API (Lambda + DynamoDB).
"""

from dataclasses import dataclass, field

from claims_core import store


class RuleViolation(Exception):
    """A request the rules refuse. The agent is shown the reason and can adapt."""


@dataclass
class Entry:
    decision: str
    payout: float
    sections: str
    reason: str
    status: str  # decided, waiting_for_sign_off, paid
    paid: float | None = None


@dataclass
class Ledger:
    """Decisions and payments. In memory here; a database table keyed by claim id in production."""

    approval_limit: float = field(default_factory=lambda: store.company()["payout_approval_limit"])
    entries: dict[str, Entry] = field(default_factory=dict)

    def record_decision(self, claim_id, decision, payout, sections, reason):
        if claim_id in self.entries:
            raise RuleViolation(f"{claim_id} already has a decision, which can't be changed")
        if decision not in ("approve", "decline", "refer"):
            raise RuleViolation(f"unknown decision {decision!r}")
        if payout < 0:
            raise RuleViolation("the payout can't be negative")
        if decision != "approve" and payout != 0:
            raise RuleViolation(f"a {decision} has a payout of 0")
        held = decision == "approve" and payout > self.approval_limit
        status = "waiting_for_sign_off" if held else "decided"
        self.entries[claim_id] = Entry(decision, payout, sections, reason, status)
        return self.entries[claim_id]

    def pay(self, claim_id, amount):
        entry = self.entries.get(claim_id)
        if entry is None or entry.decision != "approve":
            raise RuleViolation(f"{claim_id} has not been approved")
        if entry.status == "paid":
            raise RuleViolation(f"{claim_id} has already been paid")
        if entry.status == "waiting_for_sign_off":
            raise RuleViolation(
                f"a payout over ${self.approval_limit:,.0f} needs a handler's sign-off; "
                "don't try again"
            )
        if abs(amount - entry.payout) > 0.005:
            raise RuleViolation(f"the payment must equal the approved payout, {entry.payout:.2f}")
        entry.status, entry.paid = "paid", amount
        return entry

    def sign_off(self, claim_id, handler):
        """A handler releases an approval held over the limit, then it is paid."""
        entry = self.entries.get(claim_id)
        if entry is None or entry.status != "waiting_for_sign_off":
            raise RuleViolation(f"{claim_id} is not waiting for sign-off")
        entry.status, entry.paid = "paid", entry.payout
        entry.reason += f" Signed off by {handler}."
        return entry
