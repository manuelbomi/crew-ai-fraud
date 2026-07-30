"""Unit tests for the deterministic transaction structuring/velocity
pattern detection logic."""
from fraud_crew.tools.transaction_history_tool import compute_pattern_findings


def test_case_0001_flags_structuring_pattern():
    findings = compute_pattern_findings("CASE-2026-0001")
    assert findings.structuring_suspected is True
    assert findings.velocity_flag is True
    assert len(findings.flagged_transaction_ids) >= 3
    assert findings.total_flagged_amount > 0


def test_case_0002_has_no_structuring_pattern():
    findings = compute_pattern_findings("CASE-2026-0002")
    assert findings.structuring_suspected is False
    assert findings.flagged_transaction_ids == []
    assert findings.total_flagged_amount == 0.0


def test_findings_are_deterministic_across_repeated_calls():
    first = compute_pattern_findings("CASE-2026-0001")
    second = compute_pattern_findings("CASE-2026-0001")
    assert first.structuring_suspected == second.structuring_suspected
    assert first.flagged_transaction_ids == second.flagged_transaction_ids
