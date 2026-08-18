from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_fundamentals_routes_exist_in_openapi() -> None:
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]
    assert "/ticker/{symbol}/announcements" in paths
    assert "/ticker/{symbol}/financials" in paths
    assert "/ticker/{symbol}/ratios" in paths
    assert "/ticker/{symbol}/insider-trades" in paths
    assert "/ticker/{symbol}/ownership" in paths


def test_snapshot_schema_includes_phase2_fields() -> None:
    schema = client.get("/openapi.json").json()
    props = schema["components"]["schemas"]["SnapshotResponse"]["properties"]
    assert "pe_ttm" in props
    assert "eps_ttm" in props
    assert "dividend_yield" in props
    assert "free_float_pct" in props
