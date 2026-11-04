"""The shape of a decision. Both the single-call eval and the agent produce one."""

from typing import Literal

from pydantic import BaseModel, Field

Decision = Literal["approve", "decline", "refer"]


class ClaimDecision(BaseModel):
    """A claims handler's decision on one claim."""

    # The rationale comes first so the model reasons before it decides.
    rationale: str = Field(description="Two or three sentences, naming the sections relied on")
    decision: Decision
    payout: float = Field(ge=0, description="In AUD; 0 for a decline or a referral")
