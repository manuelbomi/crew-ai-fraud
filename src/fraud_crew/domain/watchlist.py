"""Pydantic models for the synthetic sanctions/watchlist screening step.

CRITICAL: every name in `fraud_crew.data.seed_watchlist` is invented for
this demo. None of it refers to any real person, organization, or actual
government sanctions list. The "list_source" field uses clearly fictional
labels (e.g. "Northbridge Internal Watch Register - SYNTHETIC") specifically
so nobody mistakes this for a real screening feed.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class WatchlistEntry(BaseModel):
    """One row of the small seeded synthetic watchlist."""

    entry_id: str
    listed_name: str
    list_source: str = Field(
        ..., description="Fictional/synthetic source label, never a real registry."
    )
    reason: str
    risk_category: str = "unspecified"


class WatchlistMatch(BaseModel):
    """Result of screening a single name against the synthetic watchlist."""

    screened_name: str
    matched_entry: WatchlistEntry | None = None
    match_score: float = Field(..., ge=0.0, le=1.0)
    is_match: bool
    match_type: str = Field(
        default="none", description="'exact' | 'fuzzy' | 'none'"
    )


class WatchlistScreeningResult(BaseModel):
    """Structured output of the WatchlistScreeningAgent's task."""

    case_id: str
    screened_names: list[str]
    matches: list[WatchlistMatch] = Field(default_factory=list)
    any_hits: bool = False
    narrative: str = ""
