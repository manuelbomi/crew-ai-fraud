# Contributing

This is a personal portfolio project, but it is built and tested like a
real one -- contributions, issues, and forks are welcome.

## Local setup

```bash
make install   # creates a venv-equivalent install + dev dependencies
make test      # runs the unit test suite
make lint      # ruff + mypy
make run       # starts the FastAPI trigger service locally
```

See the README "Getting Started" section for the full walkthrough.

## Guidelines

- Keep the layered architecture: `api/` never imports `tools/` or
  `crew/` internals directly -- go through `crew/crew_definition.py`.
  `domain/` models never import CrewAI, FastAPI, or LLM clients.
- Any change to `fraud_crew/domain/watermark.py` or to `CaseReport` must
  keep the watermark field mandatory and update
  `tests/test_report_watermark.py` in the same change.
- Any change to the compliance critique loop
  (`fraud_crew/crew/critique_loop.py`) must preserve the hard
  `max_iterations` cap and keep `tests/test_critique_loop.py` passing --
  the loop must always terminate.
- New tools should follow the pattern in `fraud_crew/tools/`: a plain,
  unit-tested Python function that computes the structured result, plus a
  thin `BaseTool` subclass that formats it for the agent's context.
- Do not add real employer names, real sanctions-list data, or real PII
  anywhere in this repository. All example data must remain synthetic and
  attributed to the fictional "Northbridge Financial Group" brand.
- Run `make lint` and `make test` before opening a PR; CI
  (`.github/workflows/ci.yml`) runs the same checks.
