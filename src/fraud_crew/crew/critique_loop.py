"""The compliance-reviewer <-> report-writer critique loop.

This is the single most important guardrail in the repo, so its control
flow is deliberately simple and entirely in plain Python:

    draft = writer.draft()
    loop, at most `max_iterations` times:
        checklist = deterministic_policy_check(draft)      # never an LLM decision
        if checklist passes OR we're on the last allowed iteration:
            return draft, review                           # ALWAYS terminates here
        draft = writer.revise(draft, checklist.feedback)

No code path in this class can loop more than `max_iterations` times --
the loop condition itself enforces the cap, not a convention the LLM is
trusted to follow. See GOVERNANCE.md item 4 and
`tests/test_critique_loop.py`, which drives this class directly with an
intentionally incomplete first draft and asserts it terminates within the
cap.
"""
from __future__ import annotations

from dataclasses import dataclass

from crewai import Agent, Task

from fraud_crew.crew.policy_checklist import evaluate_checklist
from fraud_crew.crew.report_parsing import parse_writer_output
from fraud_crew.domain.compliance import ComplianceChecklistItem, ComplianceReviewResult
from fraud_crew.domain.transaction import PatternFindings
from fraud_crew.domain.watchlist import WatchlistScreeningResult
from fraud_crew.infrastructure.audit_log import audit_log
from fraud_crew.infrastructure.logging import get_logger
from fraud_crew.infrastructure.tracing import span

logger = get_logger(__name__)

# Must match fraud_crew.infrastructure.llm.REVISION_MARKER. Duplicated as a
# plain string constant (rather than imported) to avoid a
# crew -> infrastructure -> crew import cycle; a docstring on both sides
# plus tests/test_critique_loop.py catch any drift.
REVISION_MARKER = "REVISION FEEDBACK:"


@dataclass
class WriterDraft:
    """The report writer's current draft narrative, prior to final
    CaseReport assembly."""

    summary: str
    recommended_next_step: str
    raw: str


class ComplianceCriticLoop:
    """Runs the bounded compliance-review / revision cycle for one case.

    Constructed once per investigation with the already-computed (and
    already deterministic) pattern/watchlist findings, plus the two agents
    involved. `run()` performs the actual loop.
    """

    def __init__(
        self,
        *,
        case_id: str,
        account_id: str,
        alert_type: str,
        pattern_findings: PatternFindings,
        watchlist_results: WatchlistScreeningResult,
        writer_agent: Agent,
        reviewer_agent: Agent,
        max_iterations: int,
    ) -> None:
        self._case_id = case_id
        self._account_id = account_id
        self._alert_type = alert_type
        self._pattern_findings = pattern_findings
        self._watchlist_results = watchlist_results
        self._writer_agent = writer_agent
        self._reviewer_agent = reviewer_agent
        # Defense in depth: even if a caller passes 0 or a negative number,
        # the loop still runs (and terminates after) exactly one iteration.
        self._max_iterations = max(1, max_iterations)

    # -- public API ----------------------------------------------------

    def run(
        self,
        *,
        alert_summary_text: str,
        pattern_narrative: str,
        watchlist_narrative: str,
    ) -> tuple[WriterDraft, ComplianceReviewResult, int]:
        """Produce a first draft, then critique/revise up to the
        configured cap. Always returns -- never raises solely because the
        checklist kept failing; a persistent failure is surfaced as
        `ComplianceReviewResult.escalated=True`, not an exception."""
        draft = self._draft(
            alert_summary_text, pattern_narrative, watchlist_narrative, feedback=None
        )

        iteration = 1
        while True:
            with span("crew.compliance_review", case_id=self._case_id, iteration=iteration):
                checklist = self._evaluate(draft)
                passed = all(item.passed for item in checklist)
                failed_feedback = [
                    f"{item.item_id}: {item.description}" for item in checklist if not item.passed
                ]
                commentary = self._reviewer_commentary(checklist, iteration)
                is_final_iteration = iteration >= self._max_iterations
                review = ComplianceReviewResult(
                    iteration=iteration,
                    passed=passed,
                    checklist=checklist,
                    feedback=failed_feedback,
                    reviewer_notes=commentary,
                    escalated=(not passed) and is_final_iteration,
                )
                audit_log.record(
                    case_id=self._case_id,
                    actor="ComplianceReviewerAgent",
                    action="checklist_evaluated",
                    iteration=iteration,
                    passed=passed,
                    failed_count=len(failed_feedback),
                    escalated=review.escalated,
                )
                logger.info(
                    "critique_loop.iteration_complete",
                    extra={
                        "case_id": self._case_id,
                        "iteration": iteration,
                        "passed": passed,
                        "escalated": review.escalated,
                    },
                )

            # Hard termination condition: this is the ONLY way out of the
            # loop, and it is always reachable because `iteration` only
            # increases and `is_final_iteration` becomes True once
            # `iteration == self._max_iterations`.
            if passed or is_final_iteration:
                return draft, review, iteration

            with span("crew.report_revision", case_id=self._case_id, next_iteration=iteration + 1):
                draft = self._draft(
                    alert_summary_text,
                    pattern_narrative,
                    watchlist_narrative,
                    feedback=failed_feedback,
                    previous=draft,
                )
                audit_log.record(
                    case_id=self._case_id,
                    actor="CaseReportWriterAgent",
                    action="draft_revised",
                    iteration=iteration + 1,
                )
            iteration += 1

    # -- internals -------------------------------------------------------

    def _default_next_step(self) -> str:
        """Deterministic fallback used when the writer's raw output can't
        be parsed for a RECOMMENDED_NEXT_STEP section at all."""
        if self._pattern_findings.structuring_suspected or self._watchlist_results.any_hits:
            return (
                "Escalate to a human compliance officer for manual "
                "assessment (synthetic recommendation)."
            )
        return (
            "No further escalation indicated; close as reviewed pending "
            "analyst sign-off (synthetic recommendation)."
        )

    def _evaluate(self, draft: WriterDraft) -> list[ComplianceChecklistItem]:
        return evaluate_checklist(
            account_id=self._account_id,
            summary=draft.summary,
            recommended_next_step=draft.recommended_next_step,
            pattern_findings=self._pattern_findings,
            watchlist_results=self._watchlist_results,
        )

    def _writer_prompt(
        self,
        alert_summary_text: str,
        pattern_narrative: str,
        watchlist_narrative: str,
        feedback: list[str] | None,
        previous: WriterDraft | None,
    ) -> str:
        lines = [
            f"Draft the case narrative for case {self._case_id}.",
            f"Account: {self._account_id}",
            f"Alert type: {self._alert_type}",
            f"Structuring pattern suspected: {self._pattern_findings.structuring_suspected}",
            f"Velocity flag: {self._pattern_findings.velocity_flag}",
            f"Any watchlist hits: {self._watchlist_results.any_hits}",
            "[TRIAGE DATA]",
            alert_summary_text,
            "[PATTERN DATA]",
            pattern_narrative,
            "[WATCHLIST DATA]",
            watchlist_narrative,
        ]
        if feedback:
            lines.append(REVISION_MARKER)
            lines.extend(f"- {item}" for item in feedback)
            if previous is not None:
                lines.append("[PREVIOUS DRAFT]")
                lines.append(previous.raw)
        lines.append(
            "Respond with exactly two labeled sections: 'SUMMARY: <text>' "
            "and 'RECOMMENDED_NEXT_STEP: <text>'."
        )
        return "\n".join(lines)

    def _draft(
        self,
        alert_summary_text: str,
        pattern_narrative: str,
        watchlist_narrative: str,
        feedback: list[str] | None,
        previous: WriterDraft | None = None,
    ) -> WriterDraft:
        prompt = self._writer_prompt(
            alert_summary_text, pattern_narrative, watchlist_narrative, feedback, previous
        )
        task = Task(
            description=prompt,
            expected_output="Two labeled sections: SUMMARY and RECOMMENDED_NEXT_STEP.",
            agent=self._writer_agent,
        )
        raw = str(self._writer_agent.execute_task(task))
        summary, next_step = parse_writer_output(raw, fallback_next_step=self._default_next_step())
        return WriterDraft(summary=summary, recommended_next_step=next_step, raw=raw)

    def _reviewer_commentary(self, checklist: list[ComplianceChecklistItem], iteration: int) -> str:
        passed = all(item.passed for item in checklist)
        failed = [item for item in checklist if not item.passed]
        checklist_text = "\n".join(
            f"- {item.item_id}: {item.description} (passed={item.passed}; {item.detail})"
            for item in checklist
        )
        prompt = (
            f"Compliance checklist result for case {self._case_id}, review iteration {iteration}.\n"
            f"Checklist currently passing: {passed}\n"
            f"Failed items: {len(failed)}\n"
            "[CHECKLIST DATA]\n"
            f"{checklist_text}\n"
            "Write 1-2 sentences of reviewer commentary for a human compliance officer."
        )
        task = Task(
            description=prompt,
            expected_output="1-2 sentences of reviewer commentary.",
            agent=self._reviewer_agent,
        )
        return str(self._reviewer_agent.execute_task(task))
