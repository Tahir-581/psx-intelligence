"""OpenAPI presence tests for master completion endpoints."""

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_governance_routes_in_openapi():
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]
    assert "/ticker/{symbol}/governance" in paths
    assert "/ticker/{symbol}/credit-ratings" in paths
    assert "/ticker/{symbol}/overview" in paths
    assert "/ticker/{symbol}/chart-markers" in paths
    assert "/ticker/{symbol}/corporate-actions/analytics" in paths
    assert "/ticker/{symbol}/news/volume" in paths
    assert "/notifications/preferences" in paths


def test_price_series_schema_extended():
    schema = client.get("/openapi.json").json()
    props = schema["components"]["schemas"]["PriceSeriesResponse"]["properties"]
    assert "indicator_series" in props
    assert "volume_ma" in props


def test_snapshot_schema_extended():
    schema = client.get("/openapi.json").json()
    props = schema["components"]["schemas"]["SnapshotResponse"]["properties"]
    assert "vwap" in props
    assert "board_change_30d" in props
