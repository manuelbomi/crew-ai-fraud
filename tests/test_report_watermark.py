"""Tests that the crew's final draft report always carries every required
section and the mandatory human-review watermark.

Runs the full crew (fact-gathering Crew + critique loop) end to end
against the offline MockLLM -- this is the project's primary "does the
whole thing actually work" test.
"""
import pytest

from fraud_crew.crew.crew_definition import run_investigation
from fraud_crew.domain.errors import CaseNotFoundError
from fraud_crew.domain.watermark import DRAFT_WATERMARK


def test_draft_report_has_all_required_sections_and_watermark():
    report = run_investigation("CASE-2026-0001")

    assert report.case_id == "CASE-2026-0001"
    assert report.summary
    assert report.pattern_findings is not None
    assert report.watchlist_results is not None
    assert report.compliance_notes
    assert report.recommended_next_step
    assert report.compliance_review is not None
    assert report.iterations_used >= 1
    assert report.watermark == DRAFT_WATERMARK

    # Should not raise -- defense-in-depth check called by the API layer too.
    report.require_watermark()


def test_watchlist_hit_case_produces_a_watermarked_report_too():
    report = run_investigation("CASE-2026-0002")
    assert report.watchlist_results.any_hits is True
    assert report.watermark == DRAFT_WATERMARK


def test_require_watermark_raises_if_the_field_is_ever_altered():
    report = run_investigation("CASE-2026-0001")
    report.watermark = "TAMPERED"
    with pytest.raises(ValueError):
        report.require_watermark()


def test_unknown_case_id_raises_case_not_found():
    with pytest.raises(CaseNotFoundError):
        run_investigation("CASE-DOES-NOT-EXIST")
