"""API-level tests using FastAPI's TestClient (offline, no network)."""
from fastapi.testclient import TestClient

from fraud_crew.api.main import app
from fraud_crew.domain.watermark import DRAFT_WATERMARK

client = TestClient(app)


def test_healthz_is_always_ok():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_readyz_reports_ready_with_seeded_cases():
    resp = client.get("/readyz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["seeded_case_count"] >= 1
    assert body["using_mock_llm"] is True  # no API keys in the test environment


def test_investigate_then_get_report_roundtrip():
    post_resp = client.post("/cases/CASE-2026-0001/investigate")
    assert post_resp.status_code == 200
    body = post_resp.json()
    assert body["case_id"] == "CASE-2026-0001"
    assert body["status"] in ("completed", "escalated")
    assert body["report"]["watermark"] == DRAFT_WATERMARK

    get_resp = client.get("/cases/CASE-2026-0001/report")
    assert get_resp.status_code == 200
    assert get_resp.json()["report"]["case_id"] == "CASE-2026-0001"


def test_investigate_unknown_case_id_returns_404():
    resp = client.post("/cases/CASE-DOES-NOT-EXIST/investigate")
    assert resp.status_code == 404


def test_get_report_before_investigate_returns_404():
    resp = client.get("/cases/CASE-NEVER-TRIGGERED/report")
    assert resp.status_code == 404
