"""API layer: FastAPI app, routes, and request/response schemas.

This layer knows about HTTP; nothing below it (crew/, tools/, domain/)
does. Route handlers translate between HTTP concerns (status codes,
request/response bodies) and the crew orchestration entrypoint
(`fraud_crew.crew.crew_definition.run_investigation`).
"""
