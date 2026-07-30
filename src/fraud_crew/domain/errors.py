"""Small domain-level exception types shared across the crew and API layers."""
from __future__ import annotations


class CaseNotFoundError(Exception):
    """Raised when a case_id has no seeded synthetic data.

    Deliberately not a bare KeyError: this is a domain-meaningful failure
    (the API layer maps it to HTTP 404) and a distinct exception type makes
    that mapping unambiguous instead of relying on catching a generic
    built-in that other bugs could also raise.
    """

    def __init__(self, case_id: str) -> None:
        self.case_id = case_id
        super().__init__(f"No seeded case data found for case_id={case_id!r}")
