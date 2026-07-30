"""Structured JSON logging with case/correlation-id propagation.

Why a hand-rolled JSON formatter instead of a bigger logging library: the
requirement here is narrow (structured, one-line-per-record, safe to ship
to any log aggregator) and a stdlib `logging.Formatter` subclass keeps the
dependency footprint small, which matters for a demo repo a reviewer will
`pip install` from scratch.

PII / secrecy note: `configure_logging` installs a filter that redacts any
attribute named in `_SENSITIVE_KEYS` before a record is serialized. Callers
should still avoid passing raw account numbers or full names into log
`extra=` dicts in the first place -- the filter is defense in depth, not a
substitute for care at the call site.
"""
from __future__ import annotations

import contextvars
import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

# Correlation id (== case_id, typically) threaded through a request/crew run
# via contextvars so nested calls (tools, agents, API handlers) don't need
# to explicitly pass it down just to get it into every log line.
_case_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "case_id", default=None
)

_SENSITIVE_KEYS = {
    "api_key",
    "openai_api_key",
    "anthropic_api_key",
    "authorization",
    "password",
    "secret",
    "ssn",
    "account_number",
}


def set_case_context(case_id: str | None) -> None:
    """Bind the current case id for all subsequent log records on this
    logical task/thread until changed or cleared."""
    _case_id_ctx.set(case_id)


def get_case_context() -> str | None:
    return _case_id_ctx.get()


class _JsonFormatter(logging.Formatter):
    """Renders each LogRecord as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "case_id": get_case_context(),
        }

        # Merge any structured `extra=` fields the caller supplied, redacting
        # anything that looks sensitive by key name.
        for key, value in record.__dict__.items():
            if key in (
                "args", "asctime", "created", "exc_info", "exc_text", "filename",
                "funcName", "levelname", "levelno", "lineno", "module", "msecs",
                "msg", "name", "pathname", "process", "processName", "relativeCreated",
                "stack_info", "thread", "threadName", "taskName",
            ):
                continue
            if key.lower() in _SENSITIVE_KEYS:
                payload[key] = "***REDACTED***"
            else:
                payload[key] = value

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Idempotent process-wide logging setup. Safe to call more than once
    (e.g. once from the API entrypoint, once from a test fixture)."""
    root = logging.getLogger()
    root.setLevel(level.upper())

    # Avoid duplicate handlers if configure_logging() is called twice (e.g.
    # under pytest with multiple test modules importing the app).
    if any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        return

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(_JsonFormatter())
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
