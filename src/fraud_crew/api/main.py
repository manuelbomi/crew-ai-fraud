"""FastAPI application entrypoint.

Run locally with:  uvicorn fraud_crew.api.main:app --reload
(or `make run` / `docker compose up`)

This module is intentionally thin: it wires up logging, health/readiness
endpoints, and the case router. All actual business logic lives in
`fraud_crew.crew` and below.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from fraud_crew.api.routes import router
from fraud_crew.data.seed_cases import SEED_CASES
from fraud_crew.infrastructure.config import get_settings
from fraud_crew.infrastructure.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info(
        "app.startup",
        extra={
            "app_env": settings.app_env,
            "using_mock_llm": not settings.has_real_llm_credentials,
            "seeded_case_count": len(SEED_CASES),
        },
    )
    yield
    logger.info("app.shutdown")


app = FastAPI(
    title="Fraud & AML Investigation Crew API",
    description=(
        "Decision-support DRAFTING service only. Does not file any real "
        "regulatory report and requires human compliance-officer review "
        "of every output. See README.md and GOVERNANCE.md."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/healthz", tags=["ops"], summary="Liveness probe: is the process up?")
def healthz() -> JSONResponse:
    # Deliberately has zero dependencies (no seed-data check, no LLM
    # check) -- liveness should only fail if the process itself is wedged.
    return JSONResponse({"status": "ok"})


@app.get("/readyz", tags=["ops"], summary="Readiness probe: can this instance serve traffic?")
def readyz() -> JSONResponse:
    # Readiness checks the things that would make a request fail even
    # though the process is alive: settings load fine and seed data is
    # present. Deliberately does NOT make a live LLM call -- that would
    # make readiness flaky/expensive and defeats the "runs with no API
    # keys" design goal.
    try:
        settings = get_settings()
        if not SEED_CASES:
            raise RuntimeError("no seeded cases loaded")
        return JSONResponse(
            {
                "status": "ready",
                "using_mock_llm": not settings.has_real_llm_credentials,
                "seeded_case_count": len(SEED_CASES),
            }
        )
    except Exception as exc:  # noqa: BLE001 -- readiness must never raise, only report unready
        logger.exception("readyz.failed")
        return JSONResponse({"status": "not_ready", "detail": str(exc)}, status_code=503)
