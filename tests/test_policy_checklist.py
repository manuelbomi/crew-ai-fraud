"""Unit tests for the deterministic synthetic internal policy checklist."""
from fraud_crew.crew.policy_checklist import evaluate_checklist
from fraud_crew.domain.transaction import PatternFindings
from fraud_crew.domain.watchlist import WatchlistScreeningResult


def _pattern(**overrides):
    base = dict(case_id="CASE-X", account_id="ACC-1", transactions_reviewed=5)
    base.update(overrides)
    return PatternFindings(**base)


def _watchlist(**overrides):
    base = dict(case_id="CASE-X", screened_names=["Subject X"])
    base.update(overrides)
    return WatchlistScreeningResult(**base)


def test_placeholder_next_step_fails_checklist():
    items = evaluate_checklist(
        account_id="ACC-1",
        summary=(
            "A sufficiently long draft summary that references ACC-1 and "
            "has more than fifteen words in total to satisfy the length rule."
        ),
        recommended_next_step="TBD",
        pattern_findings=_pattern(),
        watchlist_results=_watchlist(),
    )
    by_id = {i.item_id: i for i in items}
    assert by_id["next_step_actionable"].passed is False


def test_complete_draft_with_no_flags_passes_all_items():
    items = evaluate_checklist(
        account_id="ACC-1",
        summary=(
            "Reviewed account ACC-1 in detail; no structuring or watchlist "
            "concerns were identified in this synthetic case narrative."
        ),
        recommended_next_step="Close as reviewed pending analyst sign-off.",
        pattern_findings=_pattern(),
        watchlist_results=_watchlist(),
    )
    assert all(i.passed for i in items)


def test_flagged_pattern_requires_explicit_disclosure_in_summary():
    items = evaluate_checklist(
        account_id="ACC-1",
        summary=(
            "Reviewed account ACC-1 in detail with more than fifteen words "
            "but never mentions the relevant finding at all here."
        ),
        recommended_next_step="Escalate to a human compliance officer.",
        pattern_findings=_pattern(structuring_suspected=True),
        watchlist_results=_watchlist(),
    )
    by_id = {i.item_id: i for i in items}
    assert by_id["pattern_findings_disclosed"].passed is False


def test_watchlist_hit_requires_explicit_disclosure_in_summary():
    items = evaluate_checklist(
        account_id="ACC-1",
        summary=(
            "Reviewed account ACC-1 in detail with more than fifteen words "
            "but never mentions the relevant finding at all here."
        ),
        recommended_next_step="Escalate to a human compliance officer.",
        pattern_findings=_pattern(),
        watchlist_results=_watchlist(any_hits=True),
    )
    by_id = {i.item_id: i for i in items}
    assert by_id["watchlist_findings_disclosed"].passed is False
