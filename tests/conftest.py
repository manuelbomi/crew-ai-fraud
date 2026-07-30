"""Shared pytest fixtures.

The most important thing this file does is guarantee every test runs
against the deterministic offline MockLLM, regardless of what a
developer's local shell or `.env` happens to have set. Test determinism
(and CI, which never has real API keys) must not depend on ambient
environment state.
"""
import os

import pytest

# Set before any test imports fraud_crew, matching what fraud_crew/__init__.py
# itself does -- keeps a stray interactive tracing prompt from ever firing
# during a test run.
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")


@pytest.fixture(autouse=True)
def offline_settings(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    from fraud_crew.infrastructure.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
