"""HTTP routes for the fraud/AML investigation trigger service.

Design decision: POST /cases/{case_id}/investigate runs the crew
synchronously and returns the completed (or escalated) CaseRecord in the
same request/response cycle. That is a deliberate simplification for a
demo repo -- a crew run against MockLLM completes in well under a second,
and a real hosted-LLM run is still bounded (timeouts + tenacity retries
cap worst-case latency). A production deployment fielding slower or
higher-volume workloads would instead enqueue the run (e.g. via Celery/
an async task queue) and have POST return 202 Accepted immediately, with
GET /cases/{case_id}/report used for polling -- see README "Roadmap".
The route/response shape here (poll a separate GET endpoint) already
matches that future evolution, so upgrading to async execution later
would not be a breaking API change.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from fraud_crew.api.case_store import case_store
from fraud_crew.api.schemas import InvestigateRequest
from fraud_crew.crew.crew_definition import run_investigation
from fraud_crew.domain.errors import CaseNotFoundError
from fraud_crew.domain.report import CaseRecord, CaseStatus
from fraud_crew.infrastructure.logging import get_logger, set_case_context
from fraud_crew.infrastructure.tracing import span

logger = get_logger(__name__)

router = APIRouter(tags=["cases"])


@router.post(
    "/cases/{case_id}/investigate",
    response_model=CaseRecord,
    summary="Kick off the fraud/AML investigation crew for a seeded synthetic case.",
)
def investigate_case(case_id: str, _body: InvestigateRequest | None = None) -> CaseRecord:
    set_case_context(case_id)
    record = CaseRecord(case_id=case_id, status=CaseStatus.IN_PROGRESS)
    case_store.put(record)

    with span("api.investigate_case", case_id=case_id):
        try:
            report = run_investigation(case_id)
        except CaseNotFoundError as exc:
            logger.warning("api.investigate_case.not_found", extra={"case_id": case_id})
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001 -- deliberately broad: this is the API's outermost boundary
            logger.exception("api.investigate_case.failed", extra={"case_id": case_id})
            record.status = CaseStatus.FAILED
            record.error = "Investigation failed. See server logs for details."
            case_store.put(record)
            raise HTTPException(status_code=500, detail=record.error) from exc

    record.status = CaseStatus.ESCALATED if report.compliance_review.escalated else CaseStatus.COMPLETED
    record.report = report
    case_store.put(record)
    return record


@router.get(
    "/cases/{case_id}/report",
    response_model=CaseRecord,
    summary="Retrieve the draft report (and status) for a previously triggered case.",
)
def get_case_report(case_id: str) -> CaseRecord:
    record = case_store.get(case_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"No investigation found for case_id={case_id!r}. POST /cases/{case_id}/investigate first.",
        )
    return record
