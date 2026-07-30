"""The synthetic internal policy checklist the ComplianceReviewerAgent's
critique loop evaluates a draft against.

IMPORTANT: this is an illustrative, invented example of the *kind* of
checklist a bank's internal tooling might apply to a draft case narrative
before it goes to a human compliance officer. It is not derived from, and
does not implement, any specific real regulation or legal requirement --
see the README and GOVERNANCE.md disclaimers. Evaluation is deterministic
plain Python (no LLM judgment) precisely so it is reproducible and
unit-testable; see GOVERNANCE.md item 3.
"""
from __future__ import annotations

from fraud_crew.domain.compliance import ComplianceChecklistItem
from fraud_crew.domain.transaction import PatternFindings
from fraud_crew.domain.watchlist import WatchlistScreeningResult

_PLACEHOLDER_NEXT_STEPS = {"", "tbd", "todo", "n/a", "na", "pending"}
_MIN_SUMMARY_WORDS = 15
_MIN_NEXT_STEP_CHARS = 15


def evaluate_checklist(
    *,
    account_id: str,
    summary: str,
    recommended_next_step: str,
    pattern_findings: PatternFindings,
    watchlist_results: WatchlistScreeningResult,
) -> list[ComplianceChecklistItem]:
    """Deterministically evaluate a draft against the synthetic internal
    policy checklist. Pure function: same inputs always yield the same
    checklist result, which is what lets `ComplianceCriticLoop` guarantee
    reproducible, testable pass/fail behavior independent of any LLM.
    """
    items: list[ComplianceChecklistItem] = []

    # 1. Summary must be substantive, not a one-liner placeholder.
    word_count = len(summary.split())
    items.append(
        ComplianceChecklistItem(
            item_id="summary_substantive",
            description=f"Draft summary must contain at least {_MIN_SUMMARY_WORDS} words.",
            passed=word_count >= _MIN_SUMMARY_WORDS,
            detail=f"word_count={word_count}",
        )
    )

    # 2. Summary must reference the account under investigation, so a
    # human reviewer can immediately confirm it's the right case.
    references_account = account_id.lower() in summary.lower()
    items.append(
        ComplianceChecklistItem(
            item_id="summary_references_account",
            description="Draft summary must reference the account id under investigation.",
            passed=references_account,
            detail=f"account_id={account_id!r} present={references_account}",
        )
    )

    # 3. If a structuring/velocity pattern was flagged, the summary must
    # say so explicitly -- a human should never have to infer a material
    # flag from silence.
    pattern_flagged = pattern_findings.structuring_suspected or pattern_findings.velocity_flag
    mentions_pattern = any(
        kw in summary.lower() for kw in ("structuring", "velocity", "pattern")
    )
    items.append(
        ComplianceChecklistItem(
            item_id="pattern_findings_disclosed",
            description="If a transaction pattern was flagged, the summary must mention it explicitly.",
            passed=(not pattern_flagged) or mentions_pattern,
            detail=f"pattern_flagged={pattern_flagged} mentioned={mentions_pattern}",
        )
    )

    # 4. Same rule for watchlist hits.
    mentions_watchlist = "watchlist" in summary.lower() or "watch register" in summary.lower()
    items.append(
        ComplianceChecklistItem(
            item_id="watchlist_findings_disclosed",
            description="If a watchlist hit occurred, the summary must mention it explicitly.",
            passed=(not watchlist_results.any_hits) or mentions_watchlist,
            detail=f"any_hits={watchlist_results.any_hits} mentioned={mentions_watchlist}",
        )
    )

    # 5. Recommended next step must be a real, non-placeholder recommendation.
    next_step_clean = recommended_next_step.strip().lower().rstrip(".")
    has_next_step = (
        len(recommended_next_step.strip()) >= _MIN_NEXT_STEP_CHARS
        and next_step_clean not in _PLACEHOLDER_NEXT_STEPS
    )
    items.append(
        ComplianceChecklistItem(
            item_id="next_step_actionable",
            description=f"Recommended next step must be a concrete statement (>= {_MIN_NEXT_STEP_CHARS} chars, not a placeholder).",
            passed=has_next_step,
            detail=f"recommended_next_step={recommended_next_step!r}",
        )
    )

    return items
