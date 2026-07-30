"""Infrastructure layer: config, logging, tracing, audit log, and the
LLM factory (real provider vs. offline MockLLM).

Nothing in `agents/`, `tools/`, or `domain/` should import a concrete
logging framework, settings source, or LLM client directly -- they should
depend on the small interfaces exposed here. That indirection is what lets
the whole crew run fully offline in CI and in a reviewer's local clone.
"""
