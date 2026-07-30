"""Seeded synthetic cases: an initial alert + a small transaction ledger +
subject name(s) to screen, keyed by case_id.

Two cases ship by default:

- CASE-2026-0001: "Marguerite Voss" (fictional), account ACC-778812.
  Transaction history contains a classic structuring pattern (several
  cash deposits clustered just under a common reporting threshold over a
  few days) so `TransactionPatternInvestigatorTool` has something real to
  flag. The subject name does NOT appear on the seeded watchlist -- this
  is the tool's non-match test fixture.

- CASE-2026-0002: "Anya Petrov-Lindqvist" (fictional), account ACC-991245.
  Transaction history is unremarkable (no structuring/velocity flags).
  The subject name DOES appear on the seeded watchlist (see
  fraud_crew.data.seed_watchlist) -- this is the tool's match test fixture.

All names, account numbers, and amounts are synthetic. "Northbridge
Financial Group" is a wholly fictional bank brand invented for this demo.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fraud_crew.domain.alert import AlertSeverity, InitialAlert
from fraud_crew.domain.transaction import Channel, Direction, TransactionRecord

_BASE_DAY = datetime(2026, 7, 21, tzinfo=UTC)


def _ts(days: int, hour: int = 12, minute: int = 0) -> datetime:
    return _BASE_DAY + timedelta(days=days, hours=hour - 12, minutes=minute)


# ---------------------------------------------------------------------------
# CASE-2026-0001 -- structuring pattern, no watchlist hit
# ---------------------------------------------------------------------------
ALERT_0001 = InitialAlert(
    alert_id="ALERT-1001",
    case_id="CASE-2026-0001",
    account_id="ACC-778812",
    subject_display_name="Marguerite Voss",
    alert_type="structuring_suspected",
    severity=AlertSeverity.HIGH,
    triggered_at=_ts(4, 9, 15),
    raw_description=(
        "Automated monitoring flagged repeated cash deposits below the "
        "$10,000 reporting threshold within a short window on account "
        "ACC-778812 at Northbridge Financial Group (synthetic demo data)."
    ),
)

TRANSACTIONS_0001: list[TransactionRecord] = [
    TransactionRecord(
        transaction_id="TXN-0001-01", account_id="ACC-778812", timestamp=_ts(0, 10, 5),
        amount=9800.00, counterparty="Branch Teller - Northbridge #14",
        channel=Channel.CASH, direction=Direction.CREDIT,
    ),
    TransactionRecord(
        transaction_id="TXN-0001-02", account_id="ACC-778812", timestamp=_ts(1, 11, 40),
        amount=9650.00, counterparty="Branch Teller - Northbridge #22",
        channel=Channel.CASH, direction=Direction.CREDIT,
    ),
    TransactionRecord(
        transaction_id="TXN-0001-03", account_id="ACC-778812", timestamp=_ts(2, 9, 50),
        amount=9400.00, counterparty="Branch Teller - Northbridge #14",
        channel=Channel.CASH, direction=Direction.CREDIT,
    ),
    TransactionRecord(
        transaction_id="TXN-0001-04", account_id="ACC-778812", timestamp=_ts(3, 14, 10),
        amount=9925.00, counterparty="Branch Teller - Northbridge #09",
        channel=Channel.CASH, direction=Direction.CREDIT,
    ),
    TransactionRecord(
        transaction_id="TXN-0001-05", account_id="ACC-778812", timestamp=_ts(4, 8, 30),
        amount=250.00, counterparty="Groceryland Synthetic Retail",
        channel=Channel.CARD, direction=Direction.DEBIT,
    ),
]

# ---------------------------------------------------------------------------
# CASE-2026-0002 -- watchlist hit, unremarkable transaction history
# ---------------------------------------------------------------------------
ALERT_0002 = InitialAlert(
    alert_id="ALERT-1002",
    case_id="CASE-2026-0002",
    account_id="ACC-991245",
    subject_display_name="Anya Petrov-Lindqvist",
    alert_type="new_account_screening",
    severity=AlertSeverity.MEDIUM,
    triggered_at=_ts(4, 8, 0),
    raw_description=(
        "Routine periodic re-screening flagged the account holder name for "
        "manual review against Northbridge Financial Group's internal "
        "synthetic watch register (demo data)."
    ),
)

TRANSACTIONS_0002: list[TransactionRecord] = [
    TransactionRecord(
        transaction_id="TXN-0002-01", account_id="ACC-991245", timestamp=_ts(0, 9, 0),
        amount=1200.00, counterparty="Northbridge Payroll Services",
        channel=Channel.ACH, direction=Direction.CREDIT,
    ),
    TransactionRecord(
        transaction_id="TXN-0002-02", account_id="ACC-991245", timestamp=_ts(2, 17, 30),
        amount=85.50, counterparty="Riverside Synthetic Utilities Co-op",
        channel=Channel.ACH, direction=Direction.DEBIT,
    ),
    TransactionRecord(
        transaction_id="TXN-0002-03", account_id="ACC-991245", timestamp=_ts(4, 12, 0),
        amount=340.00, counterparty="Groceryland Synthetic Retail",
        channel=Channel.CARD, direction=Direction.DEBIT,
    ),
]

SEED_CASES: dict[str, dict] = {
    "CASE-2026-0001": {
        "alert": ALERT_0001,
        "transactions": TRANSACTIONS_0001,
        "screening_names": ["Marguerite Voss"],
    },
    "CASE-2026-0002": {
        "alert": ALERT_0002,
        "transactions": TRANSACTIONS_0002,
        "screening_names": ["Anya Petrov-Lindqvist"],
    },
}
