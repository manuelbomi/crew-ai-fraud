"""Domain layer: framework-agnostic Pydantic models shared across the API,
crew, and tools layers.

Architectural role
-------------------
Everything in this package is pure data + validation logic. Nothing here
imports CrewAI, FastAPI, or any LLM client. That separation matters for a
regulated-industry codebase: the *shape* of a case report, a transaction
record, or a watchlist match must be independently testable and reviewable
without needing to stand up a full agent crew or talk to a model provider.
"""
