# Governance & Guardrails

This document restates, in one place, the guardrails this repository
demonstrates. It is a companion to the disclaimer at the top of the
[README](README.md), not a replacement for it.

## 1. This is a decision-support drafting tool, not a filing system

Nothing in this codebase files, submits, or transmits any report to any
regulator, law-enforcement body, or third party. There is no outbound
integration to any real filing system anywhere in the code. Every report
object this crew produces is a draft, in memory or on local disk, pending
human review.

## 2. Every generated report is watermarked

`fraud_crew.domain.watermark.DRAFT_WATERMARK` (`"DRAFT — HUMAN REVIEW
REQUIRED — NOT FILED"`) is a required field on `CaseReport`
(`fraud_crew/domain/report.py`) with no code path that omits or overrides
it. `CaseReport.require_watermark()` is called before the API layer ever
serializes a report, as defense in depth. Unit tests assert the literal
watermark string on every generated report (`tests/test_report_watermark.py`).

## 3. Fact-finding is deterministic, not LLM judgment

Whether a transaction pattern looks like structuring, and whether a name
matches the seeded synthetic watchlist, are both computed by plain,
unit-tested Python functions (`fraud_crew/tools/transaction_history_tool.py`,
`fraud_crew/tools/watchlist_tool.py`) -- not decided by sampling an LLM.
The LLM's role is narrowly scoped to turning already-computed structured
findings into readable prose. This makes the factual backbone of every
report reproducible and independent of model variance.

## 4. A bounded, always-terminating critique loop

`fraud_crew.crew.critique_loop.ComplianceCriticLoop` runs the
ComplianceReviewerAgent against a synthetic internal policy checklist and,
on failure, sends specific feedback back to the CaseReportWriterAgent for
revision. The loop is capped at `Settings.max_compliance_iterations`
(default 3, configurable, hard-capped at 10 in `infrastructure/config.py`)
and the loop-control logic (pass/fail evaluation, iteration counting,
termination) is plain Python, not an LLM decision. If the cap is reached
without a pass, the case is marked `escalated` and handed to a human
reviewer -- the loop always terminates one way or the other; it never
spins indefinitely.

## 5. Full audit trail

Every tool computation, agent hand-off, and critique-loop iteration is
recorded via `fraud_crew.infrastructure.audit_log.audit_log` as an
append-only JSONL trail (`AUDIT_LOG_PATH`, default `audit_log.jsonl`),
keyed by `case_id`. This lets a reviewer reconstruct exactly what the
system looked at and concluded, independent of the generated prose.

## 6. Untrusted tool output

Mock transaction and watchlist data returned by tools is treated as
untrusted content injected into agent prompts (labeled `[...DATA]` blocks
in tool output; see tool docstrings), not as instructions. This mirrors
how a production deployment should treat any tool/API response that
ultimately originates outside the trust boundary of the prompt author.

## 7. Human sign-off is the point, not an afterthought

The intended operating model is: the crew produces a *draft* investigation
narrative and a compliance-reviewer pass/fail assessment; a human
compliance officer reads the draft, the checklist results, and the audit
trail, and decides what (if anything) happens next. No component of this
system is designed to, or capable of, taking that final step on its own.
