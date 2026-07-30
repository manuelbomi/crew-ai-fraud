# Security Policy

This is a personal portfolio project demonstrating engineering patterns.
It is not an officially supported product and has no SLA. That said, the
practices below are treated seriously because the target use case (bank
compliance tooling) demands it.

## Reporting a vulnerability

This repository is a standalone demo with no production deployment and no
real user data. If you spot a security issue in the code or dependency
set, please open a GitHub issue on this repository describing it. Do not
include real credentials, personal data, or anything sensitive in the
issue -- there should be none in this repo to begin with.

## Practices this repo follows

- **No secrets in source control.** All configuration is via environment
  variables loaded through `pydantic-settings`
  (`src/fraud_crew/infrastructure/config.py`). `.env` is gitignored;
  `.env.example` ships with placeholder (empty) values only.
- **Pinned dependencies.** `requirements.txt` and `pyproject.toml` pin
  exact versions so a `pip install` is reproducible and so dependency
  updates are a deliberate, reviewable diff rather than a silent drift.
- **Synthetic data only.** Every name, account number, and transaction in
  this repo is fabricated for demo purposes (see `src/fraud_crew/data/`).
  No real PII is processed, stored, or logged anywhere in this codebase.
- **Log redaction.** `fraud_crew.infrastructure.logging` redacts common
  secret/PII-shaped field names before a log record is serialized, and
  callers are expected to avoid passing raw account numbers or full names
  into `extra=` payloads in the first place.
- **Untrusted tool output.** Mock tool responses (transaction/watchlist
  data) are treated as untrusted content injected into LLM prompts, not as
  instructions -- see `GOVERNANCE.md` item 6. This is the same posture you
  should take toward any real external API response in a production agent
  system (prompt-injection defense in depth).
- **Non-root containers.** The Dockerfile runs the application as an
  unprivileged user in the final stage; see `Dockerfile`.
- **Dependency & container scanning in CI.** `.github/workflows/ci.yml`
  runs linting, type-checking, and tests on every push; adding a
  vulnerability scanner (e.g. `pip-audit`, `trivy`) is a natural next step
  -- see README "Roadmap".

## Known limitations (by design, for a demo repo)

- The offline `MockLLM` is deterministic and rule-based; it is not a
  security boundary and should not be mistaken for one.
- No authentication/authorization is implemented on the FastAPI endpoints.
  A real deployment behind a bank's perimeter would sit behind an internal
  gateway with OAuth2/mTLS -- see README "Production Deployment".
