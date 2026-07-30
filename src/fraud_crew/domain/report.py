"""The final structured draft case report -- the crew's ultimate work
product -- and the case status envelope returned by the API.

This is a decision-support DRAFTING artifact only. It does not file any
regulatory report and carries no legal effect on its own; see the
watermark field and README disclaimer.
"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from fraud_crew.domain.compliance import ComplianceReviewResult
from fraud_crew.domain.transaction import PatternFindings
from fraud_crew.domain.watchlist import WatchlistScreeningResult
from fraud_crew.domain.watermark import DRAFT_WATERMARK


class CaseStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    FAILED = "failed"


class CaseReport(BaseModel):
    """The CaseReportWriterAgent's final structured narrative.

    `watermark` deliberately has no way to be constructed without the draft
    text: it is a plain default (not a default_factory returning something
    mutable-but-overridable-by-callers-in-practice) so every code path that
    builds a CaseReport gets it for free, and tests assert on the literal
    string. Reviewers should treat any CaseReport instance in this codebase
    as inherently unfiled and requiring sign-off -- there is intentionally
    no "final"/"filed" variant of this model anywhere in the repo.
    """

    model_config = ConfigDict(frozen=False)

    case_id: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    summary: str
    pattern_findings: PatternFindings
    watchlist_results: WatchlistScreeningResult
    compliance_notes: str
    recommended_next_step: str

    compliance_review: ComplianceReviewResult
    iterations_used: int = Field(..., ge=1)

    watermark: str = DRAFT_WATERMARK

    def require_watermark(self) -> None:
        """Defense in depth: raise if something upstream ever mutated the
        watermark away from the required value. Called before the report is
        ever serialized out of the API layer."""
        if self.watermark != DRAFT_WATERMARK:
            raise ValueError(
                "CaseReport watermark was altered; refusing to emit an "
                "artifact that does not clearly read as an unfiled draft."
            )


class CaseRecord(BaseModel):
    """API-facing envelope tracking a case's lifecycle + audit trail."""

    case_id: str
    status: CaseStatus = CaseStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    report: CaseReport | None = None
    error: str | None = None
