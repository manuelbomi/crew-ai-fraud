"""API request/response models.

Response bodies reuse the domain models directly (`CaseRecord`,
`CaseReport`) rather than duplicating near-identical DTOs -- there is no
public/internal representation split in this demo worth the extra
indirection. `InvestigateRequest` exists as a placeholder validated body
(currently empty) so the endpoint has a well-defined, extensible request
contract from day one rather than accepting an untyped `{}`.
"""
from __future__ import annotations

from pydantic import BaseModel


class InvestigateRequest(BaseModel):
    """Body for POST /cases/{case_id}/investigate. Empty today by design --
    all case input is the seeded synthetic data keyed by case_id. Kept as
    a real Pydantic model (rather than no body at all) so adding optional
    parameters later (e.g. an analyst note) is a additive, non-breaking
    change."""

    pass


class ErrorResponse(BaseModel):
    detail: str
