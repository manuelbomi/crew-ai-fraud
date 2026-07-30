"""Pydantic models for the compliance-reviewer critique loop.

The critique loop is the single most important guardrail in this repo: a
synthetic "internal policy checklist" is evaluated deterministically in
`fraud_crew.crew.critique_loop.ComplianceCriticLoop` against the draft
findings, and the LOOP CONTROL (pass/fail, iteration counting, hard
termination) is plain Python -- not something an LLM is trusted to decide.
The LLM is only used to phrase human-readable reviewer commentary. See the
README "Key Design Decisions" section for the rationale.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ComplianceChecklistItem(BaseModel):
    """One line item of the synthetic internal policy checklist."""

    item_id: str
    description: str
    passed: bool
    detail: str = ""


class ComplianceReviewResult(BaseModel):
    """Outcome of a single compliance-review iteration."""

    iteration: int = Field(..., ge=1)
    passed: bool
    checklist: list[ComplianceChecklistItem] = Field(default_factory=list)
    feedback: list[str] = Field(
        default_factory=list,
        description="Specific, actionable revision requests sent back to the report writer.",
    )
    reviewer_notes: str = ""
    escalated: bool = Field(
        default=False,
        description=(
            "True when the loop hit max_iterations without passing. The case is "
            "still terminated and handed to a human reviewer -- escalation is a "
            "safety valve, not a failure of the guardrail."
        ),
    )
