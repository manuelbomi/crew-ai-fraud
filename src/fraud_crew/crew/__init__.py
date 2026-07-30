"""Crew layer: agent construction, task descriptions, the bounded
compliance critique loop, and the top-level orchestration entrypoint
(`crew_definition.run_investigation`) that the API layer calls.

This package is where CrewAI (`crewai.Agent`, `Task`, `Crew`, `Process`)
is actually used. `domain/` and `tools/` stay CrewAI-agnostic so they
remain independently testable; this package is the seam that wires them
together into an agentic system.
"""
