"""Tests for sector detail schemas and helpers."""

from datetime import date

from fastapi.testclient import TestClient

from backend.main import app
from backend.schemas.context import (
    SectorCompanyFinancials,
    SectorCompanyRow,
    SectorDetailResponse,
    SectorStatsItem,
)
from backend.services.sector import RANGE_FIELD, STATEMENT_LINE_CODES


client = TestClient(app)


def test_range_field_mapping():
    assert RANGE_FIELD["1d"] == "return_1d"
    assert RANGE_FIELD["ytd"] == "return_ytd"


def test_statement_line_codes_complete():
    expected = {
        "revenue",
        "gross_profit",
        "ebitda",
        "pat",
        "total_assets",
        "total_equity",
        "total_debt",
        "ocf",
        "capex",
    }
    assert set(STATEMENT_LINE_CODES) == expected


def test_sector_detail_response_schema():
    financials = SectorCompanyFinancials(
        revenue=1_000_000_000,
        pat=250_000_000,
        period_end=date(2024, 12, 31),
    )
    company = SectorCompanyRow(
        symbol="ENGRO",
        name="Engro Corporation",
        ltp=350.5,
        change_pct=1.25,
        market_cap=500_000_000_000,
        pe_ttm=12.5,
        eps_ttm=28.0,
        financials=financials,
    )
    stats = SectorStatsItem(
        sector="Chemical",
        company_count=15,
        total_market_cap=2_000_000_000_000,
        median_pe=14.0,
        return_1d=0.5,
        top_gainer_symbol="ENGRO",
        top_loser_symbol="FFC",
    )
    response = SectorDetailResponse(
        sector="Chemical",
        range="1d",
        trade_date=date.today(),
        stats=stats,
        companies=[company],
    )
    dumped = response.model_dump(mode="json")
    assert dumped["sector"] == "Chemical"
    assert dumped["companies"][0]["symbol"] == "ENGRO"
    assert dumped["companies"][0]["financials"]["revenue"] == 1_000_000_000
    assert dumped["stats"]["company_count"] == 15


def test_sector_detail_route_in_openapi():
    schema = client.get("/openapi.json").json()
    assert "/market/sectors/{sector}/detail" in schema["paths"]
    get_op = schema["paths"]["/market/sectors/{sector}/detail"]["get"]
    assert "SectorDetailResponse" in get_op["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]


def test_sector_detail_response_in_openapi_components():
    schema = client.get("/openapi.json").json()
    components = schema["components"]["schemas"]
    assert "SectorDetailResponse" in components
    assert "SectorCompanyRow" in components
    assert "SectorCompanyFinancials" in components
    props = components["SectorCompanyRow"]["properties"]
    assert "financials" in props
    assert "return_range" in props
