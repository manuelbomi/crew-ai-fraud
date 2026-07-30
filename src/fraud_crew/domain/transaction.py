"""Pydantic models for synthetic transaction records and the structured
output of the transaction-pattern investigation step.

Design note: whether a set of transactions looks like structuring or an
unusual velocity spike is computed deterministically in
`fraud_crew.tools.transaction_history_tool` (plain arithmetic over the
seeded synthetic ledger), NOT decided by an LLM. The agent's LLM call only
turns those already-computed flags into readable prose. This keeps the
factual determination reproducible, unit-testable, and independent of model
sampling variance -- important in a regulated-workflow context where the
same inputs must always yield the same flags.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Channel(str, Enum):
    WIRE = "wire"
    ACH = "ach"
    CASH = "cash"
    CARD = "card"
    BRANCH = "branch"


class Direction(str, Enum):
    CREDIT = "credit"
    DEBIT = "debit"


class TransactionRecord(BaseModel):
    """A single synthetic ledger entry."""

    transaction_id: str
    account_id: str
    timestamp: datetime
    amount: float = Field(..., gt=0)
    currency: str = "USD"
    counterparty: str
    channel: Channel
    direction: Direction


class PatternFindings(BaseModel):
    """Structured output of the TransactionPatternInvestigator agent's task."""

    case_id: str
    account_id: str
    transactions_reviewed: int
    structuring_suspected: bool = Field(
        default=False,
        description=(
            "True when multiple sub-threshold transactions cluster in a way "
            "consistent with structuring (deterministic rule, see tool)."
        ),
    )
    velocity_flag: bool = Field(
        default=False,
        description="True when transaction frequency spikes over the lookback window.",
    )
    total_flagged_amount: float = 0.0
    flagged_transaction_ids: list[str] = Field(default_factory=list)
    narrative: str = Field(
        default="", description="LLM-authored prose summary of the flags above."
    )
