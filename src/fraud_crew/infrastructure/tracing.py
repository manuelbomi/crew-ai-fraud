"""Lightweight tracing spans, one per crew task/tool call.

This is intentionally NOT a full OpenTelemetry integration -- pulling in
the OTel SDK plus an exporter would be overkill for a portfolio repo meant
to run with zero external services. Instead, `span()` is a context manager
that measures wall-clock duration and emits one structured log record per
span (via `fraud_crew.infrastructure.logging`), which is enough to show the
*shape* of instrumentation a reviewer would expect.

For a real deployment, swap this module's internals for
`opentelemetry-sdk` + an OTLP exporter to Grafana Tempo / Jaeger, feeding
the same span names used here (see README "Observability" section) --
call sites elsewhere in the codebase would not need to change.
"""
from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager

from fraud_crew.infrastructure.logging import get_case_context, get_logger

logger = get_logger("fraud_crew.tracing")


@contextmanager
def span(name: str, **attributes: object) -> Iterator[None]:
    """Time a block of work and emit a structured 'span' log record.

    Usage:
        with span("tool.transaction_history_lookup", account_id=account_id):
            ...
    """
    start = time.perf_counter()
    logger.info(
        "span.start",
        extra={"span_name": name, "case_id": get_case_context(), **attributes},
    )
    try:
        yield
    except Exception:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.exception(
            "span.error",
            extra={"span_name": name, "duration_ms": round(duration_ms, 2), **attributes},
        )
        raise
    else:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "span.end",
            extra={"span_name": name, "duration_ms": round(duration_ms, 2), **attributes},
        )
