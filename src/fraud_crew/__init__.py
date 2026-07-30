"""fraud_crew: a CrewAI multi-agent system for synthetic fraud/AML case
investigation support.

This top-level `__init__.py` runs before any submodule that imports
`crewai` (Python fully initializes a parent package before a submodule
import completes), so it is the one safe place to set process-wide
environment defaults that must be in effect *before* the `crewai` package
is imported anywhere.

Why this matters: CrewAI 1.x ships an opt-in tracing/telemetry feature
that, on first run in an interactive terminal, prompts the user to
enable/disable it. In a non-interactive context (CI, Docker, pytest) that
prompt has no one to answer it. Setting `CREWAI_TRACING_ENABLED=false` and
`CREWAI_DISABLE_TELEMETRY=true` up front keeps every run of this repo
fully offline and non-interactive, which is a hard requirement for a demo
that must "just run" for a reviewer with no API keys and no network
egress. We only set these if the environment hasn't already specified a
preference, so a user who explicitly wants tracing enabled can still opt
in via their own `.env`.
"""
import os

os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

__version__ = "0.1.0"
