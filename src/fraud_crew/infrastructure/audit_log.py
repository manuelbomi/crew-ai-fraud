"""Append-only audit trail of every agent/tool action taken during a case
investigation.

Governance rationale: a regulated institution's compliance function needs
to be able to reconstruct exactly what an automated system looked at and
concluded, independent of whatever prose the agents produced. This module
is intentionally boring and dependency-free (stdlib `json` + file append)
so it stays trustworthy: no ORM, no external log shipper required to make
a case's history durable and readable.

Each entry is one JSON line: {timestamp, case_id, actor, action, detail}.
`actor` is the agent/tool/component name; `action` is a short verb phrase;
`detail` is a small JSON-serializable dict. Callers must not put raw PII
into `detail` -- only aggregate/derived facts (counts, flags, ids).
"""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class AuditEntry:
    case_id: str
    actor: str
    action: str
    detail: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def to_json(self) -> str:
        return json.dumps(
            {
                "timestamp": self.timestamp,
                "case_id": self.case_id,
                "actor": self.actor,
                "action": self.action,
                "detail": self.detail,
            },
            default=str,
        )


class AuditLog:
    """Thread-safe audit recorder.

    Keeps an in-memory list per-process (cheap to query in tests / the API
    layer) AND appends to a JSONL file on disk when `path` is provided, so
    a case's full action history survives process restarts.
    """

    def __init__(self, path: str | None = None) -> None:
        self._lock = threading.Lock()
        self._entries: list[AuditEntry] = []
        self._path = Path(path) if path else None

    def record(self, case_id: str, actor: str, action: str, **detail: Any) -> AuditEntry:
        entry = AuditEntry(case_id=case_id, actor=actor, action=action, detail=detail)
        with self._lock:
            self._entries.append(entry)
            if self._path is not None:
                # Append-only: never rewrite prior lines. If this raises
                # (e.g. read-only filesystem in some deployment), we still
                # keep the in-memory copy so the request doesn't fail.
                try:
                    with self._path.open("a", encoding="utf-8") as fh:
                        fh.write(entry.to_json() + "\n")
                except OSError:
                    pass
        return entry

    def for_case(self, case_id: str) -> list[AuditEntry]:
        with self._lock:
            return [e for e in self._entries if e.case_id == case_id]

    def all_entries(self) -> list[AuditEntry]:
        with self._lock:
            return list(self._entries)


# Process-wide singleton. A demo/portfolio project does not need a DI
# container; a module-level instance keeps call sites simple while still
# being fully swappable in tests via `fraud_crew.infrastructure.audit_log.audit_log = AuditLog(...)`.
audit_log = AuditLog()
