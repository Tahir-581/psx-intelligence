"""Integration tests for Phase 3 context API endpoints."""

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_context_routes_exist_in_openapi() -> None:
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]
    assert "/ticker/{symbol}/news" in paths
    assert "/ticker/{symbol}/corporate-actions" in paths
    assert "/ticker/{symbol}/events" in paths
    assert "/ticker/{symbol}/beta" in paths
    assert "/macro/{series_code}" in paths
    assert "/market/sectors" in paths
    assert "/market/sectors/{sector}/detail" in paths
    assert "/market/corporate-calendar" in paths


def test_snapshot_schema_includes_phase3_fields() -> None:
    schema = client.get("/openapi.json").json()
    props = schema["components"]["schemas"]["SnapshotResponse"]["properties"]
    assert "beta" in props
    assert "sector_return_1m" in props
    assert "next_dividend_ex_date" in props


def test_prices_schema_includes_overlay() -> None:
    schema = client.get("/openapi.json").json()
    props = schema["components"]["schemas"]["PriceSeriesResponse"]["properties"]
    assert "overlay_bars" in props
