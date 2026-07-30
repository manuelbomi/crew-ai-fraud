"""Mock transaction-history lookup + deterministic structuring/velocity
pattern detection.

Everything this module "detects" is a simplified, illustrative heuristic
over synthetic data -- it is NOT an implementation of any specific
regulation, and the thresholds below (reporting-threshold band, lookback
window, transaction-count cutoffs) are demo constants, not legal advice or
a certified detection model. See README/GOVERNANCE.md.
"""
from __future__ import annotations

from datetime import timedelta

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from fraud_crew.data.seed_cases import SEED_CASES
from fraud_crew.domain.transaction import Channel, PatternFindings, TransactionRecord
from fraud_crew.infrastructure.audit_log import audit_log
from fraud_crew.infrastructure.logging import get_logger
from fraud_crew.infrastructure.tracing import span

logger = get_logger(__name__)

# --- Demo detection constants (illustrative only, not regulatory guidance) ---
REPORTING_THRESHOLD = 10_000.00
NEAR_THRESHOLD_FLOOR_RATIO = 0.90  # flag cash deposits in [90%, 100%) of threshold
STRUCTURING_MIN_CLUSTER = 3        # >= this many near-threshold cash deposits
STRUCTURING_LOOKBACK = timedelta(days=7)
VELOCITY_MIN_TRANSACTIONS = 4      # >= this many transactions in the lookback window
VELOCITY_LOOKBACK = timedelta(days=5)


def compute_pattern_findings(case_id: str) -> PatternFindings:
    """Pure function: deterministic pattern analysis over a case's seeded
    synthetic transaction ledger. No LLM involved -- same input always
    yields the same output, which is what makes this independently
    unit-testable and auditable.

    Raises KeyError if case_id is not in the seed data (caller should
    translate to an HTTP 404 / task failure as appropriate).
    """
    case = SEED_CASES[case_id]
    transactions: list[TransactionRecord] = case["transactions"]
    account_id: str = case["alert"].account_id

    if not transactions:
        return PatternFindings(
            case_id=case_id,
            account_id=account_id,
            transactions_reviewed=0,
            narrative="No transaction history available for this account.",
        )

    latest_ts = max(t.timestamp for t in transactions)

    # Structuring heuristic: cluster of cash deposits just under the
    # reporting threshold, within the lookback window ending at the most
    # recent transaction.
    near_threshold_cash = [
        t for t in transactions
        if t.channel == Channel.CASH
        and REPORTING_THRESHOLD * NEAR_THRESHOLD_FLOOR_RATIO <= t.amount < REPORTING_THRESHOLD
        and (latest_ts - t.timestamp) <= STRUCTURING_LOOKBACK
    ]
    structuring_suspected = len(near_threshold_cash) >= STRUCTURING_MIN_CLUSTER

    # Velocity heuristic: overall transaction density in a shorter window.
    recent_txns = [t for t in transactions if (latest_ts - t.timestamp) <= VELOCITY_LOOKBACK]
    velocity_flag = len(recent_txns) >= VELOCITY_MIN_TRANSACTIONS

    flagged = near_threshold_cash if structuring_suspected else []
    total_flagged_amount = round(sum(t.amount for t in flagged), 2)

    findings = PatternFindings(
        case_id=case_id,
        account_id=account_id,
        transactions_reviewed=len(transactions),
        structuring_suspected=structuring_suspected,
        velocity_flag=velocity_flag,
        total_flagged_amount=total_flagged_amount,
        flagged_transaction_ids=[t.transaction_id for t in flagged],
    )

    audit_log.record(
        case_id=case_id,
        actor="TransactionPatternInvestigator.tool",
        action="pattern_analysis_computed",
        transactions_reviewed=findings.transactions_reviewed,
        structuring_suspected=findings.structuring_suspected,
        velocity_flag=findings.velocity_flag,
    )
    return findings


def format_pattern_findings_text(findings: PatternFindings) -> str:
    """Render `PatternFindings` as the labeled text block both the
    `TransactionHistoryTool` and `fraud_crew.crew.crew_definition` use so
    the labels MockLLM pattern-matches on (e.g. "Structuring pattern
    suspected: True") are defined in exactly one place."""
    return (
        f"[TRANSACTION HISTORY DATA -- case {findings.case_id}]\n"
        f"Account: {findings.account_id}\n"
        f"Transactions reviewed: {findings.transactions_reviewed}\n"
        f"Structuring pattern suspected: {findings.structuring_suspected}\n"
        f"Velocity flag: {findings.velocity_flag}\n"
        f"Total flagged amount: {findings.total_flagged_amount}\n"
        f"Flagged transaction ids: {', '.join(findings.flagged_transaction_ids) or 'none'}\n"
    )


class TransactionHistoryToolInput(BaseModel):
    case_id: str = Field(..., description="The case id whose transaction history to inspect.")


class TransactionHistoryTool(BaseTool):
    """CrewAI tool wrapper around `compute_pattern_findings`.

    Attached to the TransactionPatternInvestigator agent. Returns a plain
    text summary (not raw JSON) because that is what an LLM tool-calling
    loop consumes best as context; the *authoritative* structured result
    is obtained by callers importing `compute_pattern_findings` directly
    (see fraud_crew.crew.crew_definition), not by re-parsing this string.
    """

    name: str = "transaction_history_lookup"
    description: str = (
        "Look up the synthetic transaction history for a case and report "
        "any structuring or velocity pattern flags. Input: case_id."
    )
    args_schema: type[BaseModel] = TransactionHistoryToolInput

    def _run(self, case_id: str) -> str:
        with span("tool.transaction_history_lookup", case_id=case_id):
            try:
                findings = compute_pattern_findings(case_id)
            except KeyError:
                logger.warning("tool.transaction_history_lookup.case_not_found", extra={"case_id": case_id})
                return f"No transaction history found for case_id={case_id!r}."

            # NOTE: this text is untrusted-content-shaped even though we
            # generated it ourselves -- downstream prompts should treat all
            # tool output as data to summarize, not instructions to follow
            # (see fraud_crew.crew.agents module docstring).
            return format_pattern_findings_text(findings)
