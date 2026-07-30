"""Pydantic models for the inbound synthetic fraud/AML alert and the
triage analyst's summary of it.

All data referenced anywhere in this module (account holders, alert
narratives, etc.) is synthetic and generated for this portfolio demo. It
does not describe any real person, account, or institution.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class AlertSeverity(str, Enum):
    """Coarse severity bucket assigned at alert generation time.

    Kept as a small closed enum (rather than a free-text field) so that
    downstream policy-checklist logic in the compliance reviewer can branch
    on it deterministically instead of parsing free text.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class InitialAlert(BaseModel):
    """The raw, synthetic transaction-monitoring alert that seeds a case.

    This models what a bank's transaction monitoring system might hand off
    to an investigation queue. In production this would arrive from a real
    monitoring platform; here it is loaded from `fraud_crew.data.seed_cases`.
    """

    alert_id: str
    case_id: str
    account_id: str
    subject_display_name: str = Field(
        ..., description="Synthetic account holder display name, fictional."
    )
    alert_type: str = Field(
        ..., description="e.g. 'structuring_suspected', 'velocity_spike'"
    )
    severity: AlertSeverity
    triggered_at: datetime
    raw_description: str = Field(
        ..., description="Free-text description as the monitoring system emitted it."
    )


class AlertSummary(BaseModel):
    """Structured output of the AlertTriageAnalyst agent's task.

    `narrative` is LLM-authored prose (real or mock). `key_facts` is a short
    bullet list the rest of the crew can rely on without re-reading the raw
    alert text, keeping downstream prompts small and focused.
    """

    case_id: str
    alert_id: str
    narrative: str
    key_facts: list[str] = Field(default_factory=list)
