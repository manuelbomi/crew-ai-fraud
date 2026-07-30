"""Application configuration via pydantic-settings.

All runtime configuration flows through this single `Settings` object,
sourced from environment variables (and a local `.env` file in dev). No
secret or endpoint is ever hardcoded elsewhere in the codebase -- grep the
repo for literal API keys and you should find none outside `.env.example`
(which contains only placeholder values).

If neither OPENAI_API_KEY nor ANTHROPIC_API_KEY is set, the crew factory
(`fraud_crew.infrastructure.llm.get_llm`) silently falls back to a
deterministic offline MockLLM so the whole system remains runnable with
zero paid API keys -- this is the load-bearing design decision documented
in the README.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central settings object. Instantiate via `get_settings()`, not directly,
    so the whole process shares one (cached) configuration snapshot."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- App identity / environment -----------------------------------
    app_env: str = Field(default="local", description="local | ci | staging | prod")
    app_name: str = Field(default="fraud-aml-investigation-crew")
    log_level: str = Field(default="INFO")

    # --- LLM provider configuration -------------------------------------
    # Deliberately Optional[str] with no default: presence/absence is what
    # decides whether we use a real provider or MockLLM.
    openai_api_key: str | None = Field(default=None)
    anthropic_api_key: str | None = Field(default=None)
    model_name: str = Field(
        default="gpt-4o-mini",
        description="Model id passed to the LLM provider when a real API key is present.",
    )
    llm_request_timeout_seconds: int = Field(default=30, ge=1)
    llm_max_retries: int = Field(default=3, ge=0)

    # --- Guardrail tuning -------------------------------------------------
    max_compliance_iterations: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Hard cap on compliance-reviewer <-> report-writer critique cycles.",
    )

    # --- API service --------------------------------------------------
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000, ge=1, le=65535)

    # --- Observability --------------------------------------------------
    enable_tracing_spans: bool = Field(default=True)
    audit_log_path: str = Field(default="audit_log.jsonl")

    @property
    def has_real_llm_credentials(self) -> bool:
        """True only when we can plausibly reach a real hosted model."""
        return bool(self.openai_api_key or self.anthropic_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Process-wide cached settings accessor.

    Using `lru_cache` (rather than a bare module-level singleton) makes it
    trivial to bust the cache in tests via `get_settings.cache_clear()` when
    a test needs to simulate a different environment.
    """
    return Settings()
