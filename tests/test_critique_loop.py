"""Tests for the bounded compliance critique/revision loop -- the crew's
central guardrail.

Uses the real `ComplianceCriticLoop` driving real `crewai.Agent` instances
against the deterministic offline `MockLLM`. MockLLM's report-writer
branch is deliberately designed to produce a terse, checklist-failing
first draft (see fraud_crew.infrastructure.llm.MockLLM._report_writer),
which makes these tests an honest end-to-end exercise of the loop
actually triggering a revision -- not a hand-constructed fixture standing
in for one.
"""
from fraud_crew.crew.agents import build_agents
from fraud_crew.crew.critique_loop import ComplianceCriticLoop
from fraud_crew.infrastructure.llm import MockLLM
from fraud_crew.tools.transaction_history_tool import compute_pattern_findings
from fraud_crew.tools.watchlist_tool import compute_watchlist_screening


def _build_loop(max_iterations: int) -> ComplianceCriticLoop:
    llm = MockLLM(model="mock/offline-v1")
    agents = build_agents(llm)
    pattern_findings = compute_pattern_findings("CASE-2026-0001")
    watchlist_results = compute_watchlist_screening("CASE-2026-0001", ["Marguerite Voss"])
    return ComplianceCriticLoop(
        case_id="CASE-2026-0001",
        account_id="ACC-778812",
        alert_type="structuring_suspected",
        pattern_findings=pattern_findings,
        watchlist_results=watchlist_results,
        writer_agent=agents.report_writer,
        reviewer_agent=agents.compliance_reviewer,
        max_iterations=max_iterations,
    )


def test_intentionally_incomplete_first_draft_triggers_a_revision():
    loop = _build_loop(max_iterations=3)
    draft, review, iterations_used = loop.run(
        alert_summary_text="synthetic alert summary text",
        pattern_narrative="synthetic pattern narrative text",
        watchlist_narrative="synthetic watchlist narrative text",
    )

    # MockLLM's first draft ("Case reviewed." / "TBD") always fails the
    # policy checklist, so the loop must have gone back to the writer at
    # least once before returning.
    assert iterations_used >= 2
    assert review.passed is True
    assert review.escalated is False
    assert "TBD" not in draft.recommended_next_step
    assert len(review.checklist) > 0


def test_loop_always_terminates_within_the_hard_iteration_cap():
    # max_iterations=1 gives the loop no room to request a revision even
    # though the first draft fails -- it must still terminate after
    # exactly one iteration (never loop indefinitely), surfacing the
    # unresolved case as escalated for human review.
    loop = _build_loop(max_iterations=1)
    draft, review, iterations_used = loop.run(
        alert_summary_text="synthetic alert summary text",
        pattern_narrative="synthetic pattern narrative text",
        watchlist_narrative="synthetic watchlist narrative text",
    )

    assert iterations_used == 1
    assert review.escalated is True
    assert review.passed is False


def test_max_iterations_of_zero_is_clamped_to_one_and_still_terminates():
    # Defensive edge case: a misconfigured cap of 0 (or negative) must not
    # produce a zero-iteration loop or a crash -- ComplianceCriticLoop
    # clamps to at least 1.
    loop = _build_loop(max_iterations=0)
    _, review, iterations_used = loop.run(
        alert_summary_text="x",
        pattern_narrative="y",
        watchlist_narrative="z",
    )
    assert iterations_used == 1
