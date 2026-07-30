"""CrewAI tool layer.

Each tool subclasses `crewai.tools.BaseTool` so agents can invoke it via
native LLM tool/function calling when a real model provider is configured.

Design decision (documented in the README): the *factual determination*
each tool makes (structuring flags, watchlist matches) is computed by a
plain, dependency-free Python function that lives alongside the BaseTool
subclass and is separately unit-tested. The BaseTool subclass is a thin
adapter that calls that function and formats the result as text for the
agent's context window. This keeps the regulated-relevant facts
reproducible and testable independent of any LLM's behavior, while still
giving agents genuine, invokable tools.
"""
