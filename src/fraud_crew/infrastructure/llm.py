"""LLM factory: real hosted provider vs. deterministic offline MockLLM.

This module is the single load-bearing piece of "runs with no paid API
keys": `get_llm()` returns a real `crewai.LLM` (litellm-backed, talking to
OpenAI/Anthropic/etc.) only when a credential is configured; otherwise it
returns `MockLLM`, a hand-rolled deterministic `crewai.llms.base_llm.BaseLLM`
implementation good enough to drive the whole crew end to end offline.

How MockLLM decides what to say
--------------------------------
CrewAI's agent executor calls `BaseLLM.call(..., from_agent=<Agent>,
from_task=<Task>)` on every LLM invocation (verified against crewai
1.15.x internals: `crew_agent_executor.py` always passes both). MockLLM
dispatches on `from_agent.role`, which this codebase controls (see
`fraud_crew.crew.roles`), rather than trying to regex-parse the rendered
prompt text -- far more robust than string-sniffing a ReAct-style prompt,
and it means MockLLM has zero coupling to crewai's exact prompt template.

MockLLM is intentionally template-based, not a toy language model: each
branch below turns already-computed structured facts (embedded in the
task description by the orchestration layer) into a short, readable
paragraph. It is NOT trying to sound "smart" -- it exists purely so the
crew is exercisable offline in CI and by a reviewer with zero API keys.
"""
from __future__ import annotations

import re
from typing import Any

from crewai import LLM
from crewai.llms.base_llm import BaseLLM
from crewai.utilities.types import LLMMessage
from pydantic import PrivateAttr
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from fraud_crew.crew.roles import (
    ROLE_ALERT_TRIAGE,
    ROLE_COMPLIANCE_REVIEWER,
    ROLE_PATTERN_INVESTIGATOR,
    ROLE_REPORT_WRITER,
    ROLE_WATCHLIST_SCREENING,
)
from fraud_crew.infrastructure.config import Settings
from fraud_crew.infrastructure.logging import get_logger

logger = get_logger(__name__)

# Marker the report-writer revision task always includes in its prompt so
# MockLLM can tell "first draft" apart from "revision" deterministically,
# without any hidden state. See fraud_crew.crew.critique_loop.
REVISION_MARKER = "REVISION FEEDBACK:"


def _flatten_messages(messages: str | list[LLMMessage]) -> str:
    """Collapse the message list CrewAI hands to BaseLLM.call() into one
    searchable string. MockLLM only ever substring-searches this for
    facts *we* embedded in the prompt (e.g. "Structuring pattern
    suspected: True") -- it never tries to parse arbitrary natural
    language, which keeps it fast and 100% deterministic."""
    if isinstance(messages, str):
        return messages
    return "\n".join(str(m.get("content", "")) for m in messages if isinstance(m, dict))


def _extract(pattern: str, text: str, default: str = "unknown") -> str:
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else default


def _bool_fact(label: str, text: str) -> bool:
    return bool(re.search(rf"{re.escape(label)}\s*:\s*True", text, re.IGNORECASE))


class MockLLM(BaseLLM):
    """Deterministic, offline, template-based stand-in for a hosted LLM.

    Used automatically whenever no OPENAI_API_KEY / ANTHROPIC_API_KEY is
    configured (see `get_llm` below). Every branch is pure string
    templating over facts already computed deterministically elsewhere in
    the codebase -- this class makes no judgment calls of its own.
    """

    def call(
        self,
        messages: str | list[LLMMessage],
        tools: list[dict] | None = None,
        callbacks: list[Any] | None = None,
        available_functions: dict[str, Any] | None = None,
        from_task: Any | None = None,
        from_agent: Any | None = None,
        response_model: Any | None = None,
    ) -> str:
        role = getattr(from_agent, "role", None)
        text = _flatten_messages(messages)

        if role == ROLE_ALERT_TRIAGE:
            return self._alert_triage(text)
        if role == ROLE_PATTERN_INVESTIGATOR:
            return self._pattern_narrative(text)
        if role == ROLE_WATCHLIST_SCREENING:
            return self._watchlist_narrative(text)
        if role == ROLE_COMPLIANCE_REVIEWER:
            return self._compliance_commentary(text)
        if role == ROLE_REPORT_WRITER:
            return self._report_writer(text)

        # Generic fallback for any agent role this build doesn't know
        # about yet -- keeps the mock forward-compatible rather than
        # raising, at the cost of a less specific answer.
        return "Acknowledged (offline MockLLM generic response)."

    # -- per-role templates ------------------------------------------------

    def _alert_triage(self, text: str) -> str:
        subject = _extract(r"Subject:\s*(.+)", text)
        account = _extract(r"Account:\s*(.+)", text)
        alert_type = _extract(r"Alert type:\s*(.+)", text)
        severity = _extract(r"Severity:\s*(.+)", text)
        return (
            f"Synthetic alert triage summary: a {severity}-severity "
            f"'{alert_type}' alert was raised on account {account} "
            f"(subject: {subject}). This narrative is generated from "
            f"synthetic demo data for a fictional bank and requires human "
            f"analyst review before any action is taken."
        )

    def _pattern_narrative(self, text: str) -> str:
        structuring = _bool_fact("Structuring pattern suspected", text)
        velocity = _bool_fact("Velocity flag", text)
        reviewed = _extract(r"Transactions reviewed:\s*(\d+)", text, default="0")
        if structuring or velocity:
            flags = ", ".join(
                f for f, present in (("structuring", structuring), ("velocity", velocity)) if present
            )
            return (
                f"Reviewed {reviewed} synthetic transactions for this account. "
                f"Pattern analysis flags: {flags}. These are illustrative, "
                f"rule-based flags over demo data, not a regulatory finding, "
                f"and require analyst verification."
            )
        return (
            f"Reviewed {reviewed} synthetic transactions for this account. "
            f"No structuring or velocity pattern flags were raised by the "
            f"deterministic pattern-detection logic."
        )

    def _watchlist_narrative(self, text: str) -> str:
        any_hits = _bool_fact("Any hits", text)
        if any_hits:
            return (
                "Watchlist screening against the synthetic internal watch "
                "register returned at least one potential match. This is a "
                "demo-data match only and requires human confirmation before "
                "any escalation."
            )
        return (
            "Watchlist screening against the synthetic internal watch "
            "register returned no matches for the screened name(s)."
        )

    def _compliance_commentary(self, text: str) -> str:
        passed = _bool_fact("Checklist currently passing", text)
        failed_count = _extract(r"Failed items:\s*(\d+)", text, default="0")
        if passed:
            return (
                "Compliance checklist review: all synthetic internal policy "
                "checklist items are satisfied. Recommending this draft "
                "proceed to human compliance-officer review."
            )
        return (
            f"Compliance checklist review: {failed_count} checklist item(s) "
            f"not yet satisfied. Returning to the report writer with "
            f"specific revision feedback before this draft can proceed to "
            f"human review."
        )

    def _report_writer(self, text: str) -> str:
        account = _extract(r"Account:\s*(.+)", text)
        alert_type = _extract(r"Alert type:\s*(.+)", text)
        structuring = _bool_fact("Structuring pattern suspected", text)
        any_hits = _bool_fact("Any watchlist hits", text)

        if REVISION_MARKER in text:
            # Revision pass: produce a fuller narrative that satisfies the
            # policy checklist (mentions account, alert type, and the
            # relevant flags explicitly; a concrete next step).
            findings_note = "a structuring pattern flag" if structuring else "no structuring pattern flag"
            watchlist_note = "a watchlist match" if any_hits else "no watchlist match"
            next_step = (
                "Escalate to a human compliance officer for manual SAR-drafting "
                "assessment (synthetic recommendation)."
                if (structuring or any_hits)
                else "No further escalation indicated; close as reviewed pending "
                "analyst sign-off (synthetic recommendation)."
            )
            return (
                f"SUMMARY: Revised synthetic case narrative for account {account} "
                f"following a '{alert_type}' alert. Investigation found {findings_note} "
                f"and {watchlist_note} against the synthetic watch register. This "
                f"draft was revised to incorporate compliance-reviewer feedback and "
                f"remains subject to human review before any action is taken.\n"
                f"RECOMMENDED_NEXT_STEP: {next_step}"
            )

        # First-pass draft: deliberately terse. This is a demo-mode design
        # choice (documented in README/GOVERNANCE) so a fresh clone of this
        # repo, running fully offline, visibly exercises the compliance
        # critique/revision loop rather than always passing on iteration 1.
        return "SUMMARY: Case reviewed.\nRECOMMENDED_NEXT_STEP: TBD"


class ResilientLLM(BaseLLM):
    """Wraps a real provider-backed `crewai.LLM` with tenacity retry
    (exponential backoff + jitter) so a transient network/provider error
    doesn't fail an entire crew run.

    Only used on the real-provider path -- MockLLM calls are local and
    don't need retry logic. `_inner`/`_max_retries` are PrivateAttr (not
    pydantic fields) since `crewai.LLM` is not itself meant to be a public
    field of another model.
    """

    _inner: LLM = PrivateAttr()
    _max_retries: int = PrivateAttr(default=3)

    def __init__(self, inner: LLM, max_retries: int = 3, **data: Any) -> None:
        super().__init__(model=inner.model, **data)
        self._inner = inner
        self._max_retries = max_retries

    def call(
        self,
        messages: str | list[LLMMessage],
        tools: list[dict] | None = None,
        callbacks: list[Any] | None = None,
        available_functions: dict[str, Any] | None = None,
        from_task: Any | None = None,
        from_agent: Any | None = None,
        response_model: Any | None = None,
    ) -> str | Any:
        @retry(
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential_jitter(initial=1, max=15),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        )
        def _do_call() -> str | Any:
            return self._inner.call(
                messages,
                tools=tools,
                callbacks=callbacks,
                available_functions=available_functions,
                from_task=from_task,
                from_agent=from_agent,
                response_model=response_model,
            )

        return _do_call()


def _resolve_model_string(settings: Settings) -> str:
    """Best-effort mapping from Settings to a litellm-style model string.

    Kept intentionally simple: this repo optimizes for "runs offline with
    zero keys" as the primary path. If you configure a real provider, you
    may need to adjust MODEL_NAME to match litellm's naming convention for
    that provider (see https://docs.litellm.ai/docs/providers).
    """
    if settings.openai_api_key:
        return settings.model_name
    if settings.anthropic_api_key and "/" not in settings.model_name:
        return f"anthropic/{settings.model_name}"
    return settings.model_name


def get_llm(settings: Settings) -> BaseLLM:
    """Return the LLM this process should use for every agent.

    Real credentials present -> a retry-wrapped `crewai.LLM` talking to the
    configured provider. Otherwise -> the deterministic offline `MockLLM`.
    This is the one function that decides "offline demo mode" vs. "real
    model" for the whole crew.
    """
    if settings.has_real_llm_credentials:
        logger.info("llm.factory.using_real_provider", extra={"model": settings.model_name})
        inner = LLM(
            model=_resolve_model_string(settings),
            api_key=settings.openai_api_key or settings.anthropic_api_key,
            timeout=settings.llm_request_timeout_seconds,
        )
        return ResilientLLM(inner=inner, max_retries=settings.llm_max_retries)

    logger.info("llm.factory.using_mock_llm")
    return MockLLM(model="mock/offline-v1")
