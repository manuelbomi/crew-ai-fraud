"""Watermark constants.

Every artifact this system generates is decision-support only. The literal
watermark text below is asserted on in unit tests (see
tests/test_report_watermark.py) so that a future refactor cannot silently
drop or reword it. Treat any change to this string as a breaking change that
requires updating the tests and the README disclaimer in lockstep.
"""

# NOTE: This exact string is contractually relied upon by tests and by the
# CaseReport.watermark default factory. Do not alter without updating both.
DRAFT_WATERMARK: str = "DRAFT — HUMAN REVIEW REQUIRED — NOT FILED"
