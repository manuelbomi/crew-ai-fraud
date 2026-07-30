"""In-memory case record store used by the API layer.

A demo/portfolio project has no business standing up Postgres just to
track a handful of synthetic case runs -- this is a thread-safe
dictionary behind a small interface, swappable for a real datastore
(e.g. Postgres via SQLAlchemy) without touching route handlers, since
callers only see `get`/`put`/`list_ids`.

State does not persist across process restarts. That is an explicit,
documented limitation (see README "Roadmap"), not an oversight.
"""
from __future__ import annotations

import threading

from fraud_crew.domain.report import CaseRecord


class CaseStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: dict[str, CaseRecord] = {}

    def get(self, case_id: str) -> CaseRecord | None:
        with self._lock:
            return self._records.get(case_id)

    def put(self, record: CaseRecord) -> None:
        with self._lock:
            self._records[record.case_id] = record

    def list_ids(self) -> list[str]:
        with self._lock:
            return list(self._records.keys())


# Process-wide singleton, mirroring fraud_crew.infrastructure.audit_log's
# pattern -- simple and adequate for a single-process demo deployment.
case_store = CaseStore()
