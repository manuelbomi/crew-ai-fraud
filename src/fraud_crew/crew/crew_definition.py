"""Top-level orchestration entrypoint: `run_investigation(case_id)`.

This is the one function the API layer calls. It wires together, in
order:

1. A real `crewai.Crew` (Process.sequential) running the AlertTriage,
   TransactionPatternInvestigator, and WatchlistScreeningAgent tasks, each
   handed the deterministically pre-computed structured findings as
   grounding context (see module docstrings in `fraud_crew.tools` for why
   the facts are computed in code, not decided by the LLM).
2. `ComplianceCriticLoop`, a hand-rolled bounded loop (not expressible as
   a plain CrewAI sequential/hierarchical Process) that alternates the
   ComplianceReviewerAgent and CaseReportWriterAgent until the synthetic
   policy checklist passes or the iteration cap is hit.
3. Final assembly of the watermarked `CaseReport`.

Every stage is wrapped in a tracing span and records to the audit log,
keyed by case_id, so the whole run is reconstructable after the fact.
"""
from __future__ import annotations

from crewai import Crew, Process, Task

from fraud_crew.crew.agents import build_agents
from fraud_crew.crew.critique_loop import ComplianceCriticLoop
from fraud_crew.data.seed_cases import SEED_CASES
from fraud_crew.domain.alert import AlertSummary
from fraud_crew.domain.errors import CaseNotFoundError
from fraud_crew.domain.report import CaseReport
from fraud_crew.infrastructure.audit_log import audit_log
from fraud_crew.infrastructure.config import Settings, get_settings
from fraud_crew.infrastructure.llm import get_llm
from fraud_crew.infrastructure.logging import get_logger, set_case_context
from fraud_crew.infrastructure.tracing import span
from fraud_crew.tools.transaction_history_tool import compute_pattern_findings, format_pattern_findings_text
from fraud_crew.tools.watchlist_tool import compute_watchlist_screening, format_watchlist_result_text

logger = get_logger(__name__)


def _alert_triage_description(alert) -> str:  # alert: InitialAlert
    return (
        f"Summarize the following synthetic fraud/AML alert for case {alert.case_id} "
        "in 2-4 sentences, in plain language for a human investigator.\n"
        "[ALERT DATA]\n"
        f"Subject: {alert.subject_display_name}\n"
        f"Account: {alert.account_id}\n"
        f"Alert type: {alert.alert_type}\n"
        f"Severity: {alert.severity.value}\n"
        f"Raw description: {alert.raw_description}\n"
    )


def _pattern_task_description(findings_text: str) -> str:
    return (
        "Explain the following pre-computed transaction pattern analysis in "
        "plain language for a human investigator. Do not invent new flags; "
        "only explain what is reported below.\n" + findings_text
    )


def _watchlist_task_description(result_text: str) -> str:
    return (
        "Explain the following pre-computed watchlist screening result in "
        "plain language for a human investigator. Do not invent new matches; "
        "only explain what is reported below.\n" + result_text
    )


def _task_output_text(task: Task) -> str:
    """Safely extract the raw text of a completed Task's output.

    `Task.output` is typed `TaskOutput | None` because a Task that hasn't
    run yet has no output -- but by the time we call this, `crew.kickoff()`
    has already executed every task in the sequential process, so `None`
    here would indicate a genuine internal bug, not a normal state. Raising
    a clear error is preferable to silently coercing `None` to the string
    "None" and shipping it into a case narrative.
    """
    if task.output is None:
        raise RuntimeError(
            "Expected a completed Task.output after Crew.kickoff(), got None. "
            "This indicates an internal orchestration bug."
        )
    return str(task.output.raw)


def run_investigation(case_id: str, settings: Settings | None = None) -> CaseReport:
    """Run the full fraud/AML investigation crew for one seeded synthetic
    case and return a watermarked draft `CaseReport`.

    Raises `CaseNotFoundError` if `case_id` isn't in the seed data set.
    """
    settings = settings or get_settings()
    set_case_context(case_id)

    if case_id not in SEED_CASES:
        raise CaseNotFoundError(case_id)

    case = SEED_CASES[case_id]
    alert = case["alert"]
    screening_names: list[str] = case["screening_names"]

    llm = get_llm(settings)
    agents = build_agents(llm)

    audit_log.record(case_id=case_id, actor="crew_definition", action="investigation_started")

    # ---- Stage 1: deterministic fact-gathering (real Crew, sequential) --
    # The tool computations happen up front (pure functions, no LLM) so the
    # narrative-writing tasks always have grounded, correct facts to work
    # from regardless of what the configured LLM does with its attached
    # tool. See fraud_crew/tools/*.py module docstrings for the rationale.
    with span("crew.fact_gathering", case_id=case_id):
        pattern_findings = compute_pattern_findings(case_id)
        watchlist_results = compute_watchlist_screening(case_id, screening_names)

        triage_task = Task(
            description=_alert_triage_description(alert),
            expected_output="A 2-4 sentence plain-language alert summary.",
            agent=agents.triage,
        )
        pattern_task = Task(
            description=_pattern_task_description(format_pattern_findings_text(pattern_findings)),
            expected_output="A short plain-language explanation of the pattern findings.",
            agent=agents.pattern_investigator,
            context=[triage_task],
        )
        watchlist_task = Task(
            description=_watchlist_task_description(format_watchlist_result_text(watchlist_results)),
            expected_output="A short plain-language explanation of the watchlist screening result.",
            agent=agents.watchlist_screener,
            context=[triage_task],
        )

        fact_finding_crew = Crew(
            agents=[agents.triage, agents.pattern_investigator, agents.watchlist_screener],
            tasks=[triage_task, pattern_task, watchlist_task],
            process=Process.sequential,
            verbose=False,
        )
        fact_finding_crew.kickoff(inputs={"case_id": case_id})

        alert_summary = AlertSummary(
            case_id=case_id,
            alert_id=alert.alert_id,
            narrative=_task_output_text(triage_task),
            key_facts=[
                f"account={alert.account_id}",
                f"alert_type={alert.alert_type}",
                f"severity={alert.severity.value}",
            ],
        )
        pattern_findings.narrative = _task_output_text(pattern_task)
        watchlist_results.narrative = _task_output_text(watchlist_task)

        audit_log.record(
            case_id=case_id,
            actor="crew_definition",
            action="fact_gathering_complete",
            structuring_suspected=pattern_findings.structuring_suspected,
            velocity_flag=pattern_findings.velocity_flag,
            any_watchlist_hits=watchlist_results.any_hits,
        )

    # ---- Stage 2: bounded compliance critique / revision loop -----------
    with span("crew.critique_loop", case_id=case_id):
        loop = ComplianceCriticLoop(
            case_id=case_id,
            account_id=alert.account_id,
            alert_type=alert.alert_type,
            pattern_findings=pattern_findings,
            watchlist_results=watchlist_results,
            writer_agent=agents.report_writer,
            reviewer_agent=agents.compliance_reviewer,
            max_iterations=settings.max_compliance_iterations,
        )
        draft, review, iterations_used = loop.run(
            alert_summary_text=alert_summary.narrative,
            pattern_narrative=pattern_findings.narrative,
            watchlist_narrative=watchlist_results.narrative,
        )

    # ---- Stage 3: final watermarked report assembly ---------------------
    report = CaseReport(
        case_id=case_id,
        summary=draft.summary,
        pattern_findings=pattern_findings,
        watchlist_results=watchlist_results,
        compliance_notes=review.reviewer_notes,
        recommended_next_step=draft.recommended_next_step,
        compliance_review=review,
        iterations_used=iterations_used,
    )
    report.require_watermark()  # defense in depth; see CaseReport docstring

    audit_log.record(
        case_id=case_id,
        actor="crew_definition",
        action="investigation_complete",
        iterations_used=iterations_used,
        escalated=review.escalated,
    )
    logger.info(
        "investigation.complete",
        extra={"case_id": case_id, "iterations_used": iterations_used, "escalated": review.escalated},
    )

    return report
