"""Phase 4 intelligence API contract tests."""

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_openapi_phase4_routes_exist():
    spec = client.get("/openapi.json").json()
    paths = spec["paths"]
    assert "/ticker/{symbol}/sentiment" in paths
    assert "/ticker/{symbol}/summary" in paths
    assert "/ticker/{symbol}/social" in paths
    assert "/watchlist" in paths
    assert "/billing/create-checkout-session" in paths
    assert "/admin/scraper-health" in paths
    assert "/admin/parser-review" in paths


def test_sentiment_requires_pro():
    resp = client.get("/ticker/ENGRO/sentiment")
    assert resp.status_code in (401, 403, 404, 422)


def test_admin_requires_key():
    resp = client.get("/admin/scraper-health")
    assert resp.status_code == 403
