"""Canonical agent role strings, shared by `fraud_crew.crew.agents` (which
constructs the `crewai.Agent` instances) and `fraud_crew.infrastructure.llm`
(whose MockLLM dispatches templated responses by role).

Keeping these as constants in one place -- rather than repeating the
literal strings in both modules -- means a rename can't silently break the
offline mock path (MockLLM would fall through to its generic fallback
response and the mismatch would be obvious in tests/logs, not a silent
divergence).
"""

ROLE_ALERT_TRIAGE = "Alert Triage Analyst"
ROLE_PATTERN_INVESTIGATOR = "Transaction Pattern Investigator"
ROLE_WATCHLIST_SCREENING = "Watchlist Screening Agent"
ROLE_COMPLIANCE_REVIEWER = "Compliance Reviewer"
ROLE_REPORT_WRITER = "Case Report Writer"
