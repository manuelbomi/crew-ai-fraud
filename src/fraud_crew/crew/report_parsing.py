"""Tolerant parsing of the CaseReportWriterAgent's raw text output into
(summary, recommended_next_step).

The writer agent is instructed (see `fraud_crew.crew.agents`) to respond
with two labeled sections, `SUMMARY:` and `RECOMMENDED_NEXT_STEP:`. Real
LLMs mostly follow formatting instructions but not always perfectly, so
this parser degrades gracefully: if the labels aren't found, the entire
response becomes the summary and a caller-supplied deterministic default
is used for the next step, rather than raising. A missing/malformed
section should never crash a case investigation -- worst case, the
compliance checklist will simply flag the placeholder-shaped next step and
the critique loop will request a revision.
"""
from __future__ import annotations

import re

_SUMMARY_RE = re.compile(
    r"SUMMARY:\s*(.*?)(?:\n\s*RECOMMENDED_NEXT_STEP:|\Z)", re.IGNORECASE | re.DOTALL
)
_NEXT_STEP_RE = re.compile(r"RECOMMENDED_NEXT_STEP:\s*(.*)", re.IGNORECASE | re.DOTALL)


def parse_writer_output(raw: str, *, fallback_next_step: str) -> tuple[str, str]:
    """Return (summary, recommended_next_step) extracted from `raw`."""
    summary_match = _SUMMARY_RE.search(raw)
    next_step_match = _NEXT_STEP_RE.search(raw)

    summary = summary_match.group(1).strip() if summary_match else raw.strip()
    next_step = next_step_match.group(1).strip() if next_step_match else fallback_next_step

    return summary, next_step
