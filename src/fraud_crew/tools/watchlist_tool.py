"""Mock sanctions/watchlist screening tool.

Screens a name against the small SYNTHETIC watchlist in
`fraud_crew.data.seed_watchlist`. Uses exact (case-insensitive) matching
first, then a fuzzy fallback (stdlib `difflib`, no extra dependency) so a
near-miss spelling still surfaces as a lower-confidence match for a human
to look at -- exactly the kind of thing you do NOT want an LLM silently
deciding on its own in a compliance context.

Reminder: the watchlist is 100% fictional demo data. See
fraud_crew/data/seed_watchlist.py.
"""
from __future__ import annotations

from difflib import SequenceMatcher

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from fraud_crew.data.seed_watchlist import SEED_WATCHLIST
from fraud_crew.domain.watchlist import WatchlistMatch, WatchlistScreeningResult
from fraud_crew.infrastructure.audit_log import audit_log
from fraud_crew.infrastructure.logging import get_logger
from fraud_crew.infrastructure.tracing import span

logger = get_logger(__name__)

FUZZY_MATCH_THRESHOLD = 0.85  # SequenceMatcher ratio at/above this counts as a "fuzzy" hit


def _score(a: str, b: str) -> float:
    return SequenceMatcher(None, a.strip().lower(), b.strip().lower()).ratio()


def screen_name(name: str) -> WatchlistMatch:
    """Pure function: screen a single name against the seeded synthetic
    watchlist. Deterministic given the fixed seed list."""
    best_entry = None
    best_score = 0.0
    match_type = "none"

    for entry in SEED_WATCHLIST:
        if name.strip().lower() == entry.listed_name.strip().lower():
            return WatchlistMatch(
                screened_name=name,
                matched_entry=entry,
                match_score=1.0,
                is_match=True,
                match_type="exact",
            )
        score = _score(name, entry.listed_name)
        if score > best_score:
            best_score = score
            best_entry = entry

    if best_entry is not None and best_score >= FUZZY_MATCH_THRESHOLD:
        match_type = "fuzzy"
        return WatchlistMatch(
            screened_name=name,
            matched_entry=best_entry,
            match_score=round(best_score, 3),
            is_match=True,
            match_type=match_type,
        )

    return WatchlistMatch(
        screened_name=name,
        matched_entry=None,
        match_score=round(best_score, 3),
        is_match=False,
        match_type="none",
    )


def compute_watchlist_screening(case_id: str, names: list[str]) -> WatchlistScreeningResult:
    """Pure function: screen every provided name and assemble the case-level
    result. No LLM involved -- see module docstring for rationale."""
    matches = [screen_name(n) for n in names]
    result = WatchlistScreeningResult(
        case_id=case_id,
        screened_names=names,
        matches=matches,
        any_hits=any(m.is_match for m in matches),
    )
    audit_log.record(
        case_id=case_id,
        actor="WatchlistScreeningAgent.tool",
        action="watchlist_screening_computed",
        screened_count=len(names),
        any_hits=result.any_hits,
    )
    return result


def format_watchlist_result_text(result: WatchlistScreeningResult) -> str:
    """Render `WatchlistScreeningResult` as the labeled text block both the
    `WatchlistScreeningTool` and `fraud_crew.crew.crew_definition` use, so
    the label MockLLM matches on ("Any hits: True/False") is defined once."""
    lines = [f"[WATCHLIST SCREENING DATA -- case {result.case_id}]"]
    for m in result.matches:
        if m.is_match and m.matched_entry is not None:
            lines.append(
                f"- '{m.screened_name}': MATCH ({m.match_type}, score={m.match_score}) "
                f"against synthetic entry {m.matched_entry.entry_id} "
                f"'{m.matched_entry.listed_name}' [{m.matched_entry.list_source}]"
            )
        else:
            lines.append(f"- '{m.screened_name}': no match (best score={m.match_score})")
    lines.append(f"Any hits: {result.any_hits}")
    return "\n".join(lines)


class WatchlistScreeningToolInput(BaseModel):
    case_id: str = Field(..., description="The case id being screened.")
    names: list[str] = Field(..., description="Subject names to screen against the watchlist.")


class WatchlistScreeningTool(BaseTool):
    """CrewAI tool wrapper around `compute_watchlist_screening`.

    Attached to the WatchlistScreeningAgent. As with the transaction-history
    tool, this returns human-readable text for the agent's context; the
    orchestration layer obtains the authoritative structured result by
    calling `compute_watchlist_screening` directly.
    """

    name: str = "watchlist_screening_lookup"
    description: str = (
        "Screen one or more subject names against the synthetic internal "
        "watchlist. Input: case_id and a list of names."
    )
    args_schema: type[BaseModel] = WatchlistScreeningToolInput

    def _run(self, case_id: str, names: list[str]) -> str:
        with span("tool.watchlist_screening_lookup", case_id=case_id, name_count=len(names)):
            result = compute_watchlist_screening(case_id, names)
            return format_watchlist_result_text(result)
