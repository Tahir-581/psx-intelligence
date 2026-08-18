"""Phase 5 API contract tests."""

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_openapi_phase5_routes_exist():
    spec = client.get("/openapi.json").json()
    paths = spec["paths"]
    assert "/screener" in paths
    assert "/screener/presets" in paths
    assert "/screener/export" in paths
    assert "/alerts" in paths
    assert "/alerts/events" in paths
    assert "/notifications" in paths
    assert "/portfolio" in paths
    assert "/compare" in paths
    assert "/ticker/{symbol}/peers" in paths
    assert "/api-keys" in paths


def test_screener_post_schema_only():
    spec = client.get("/openapi.json").json()
    assert "/screener" in spec["paths"]
    post = spec["paths"]["/screener"]["post"]
    assert post["requestBody"] is not None


def test_portfolio_requires_pro():
    resp = client.get("/portfolio")
    assert resp.status_code in (401, 403)


def test_alerts_requires_pro():
    resp = client.get("/alerts")
    assert resp.status_code in (401, 403)


def test_compare_min_symbols():
    resp = client.get("/compare?symbols=ENGRO")
    assert resp.status_code == 422
