"""Unit tests for macro seed data and SBP page parsing."""

from decimal import Decimal
from pathlib import Path

from bs4 import BeautifulSoup

from scrapers.macro.run import (
    SEED_MACRO,
    parse_pkr_usd_rate,
    parse_sbp_macro_from_text,
    parse_sbp_policy_rate,
    validate_pkr_usd,
    validate_policy_rate,
)

FIXTURE_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "sbp_ecodata_index2.html"


def _fixture_text() -> str:
    html = FIXTURE_PATH.read_text(encoding="utf-8")
    return BeautifulSoup(html, "lxml").get_text(" ", strip=True)


def test_seed_macro_has_required_series():
    codes = {item["series_code"] for item in SEED_MACRO}
    assert "sbp_policy_rate" in codes
    assert "cpi_yoy" in codes
    assert "pkr_usd" in codes


def test_seed_macro_has_current_fallback_values():
    policy_entries = [item for item in SEED_MACRO if item["series_code"] == "sbp_policy_rate"]
    fx_entries = [item for item in SEED_MACRO if item["series_code"] == "pkr_usd"]
    latest_policy = max(policy_entries, key=lambda item: item["time"])
    latest_fx = max(fx_entries, key=lambda item: item["time"])
    assert latest_policy["value"] == "11.5"
    assert latest_fx["value"] == "278.4"


def test_parse_sbp_policy_rate_from_fixture():
    text = _fixture_text()
    assert parse_sbp_policy_rate(text) == Decimal("11.50")


def test_parse_pkr_usd_ignores_bond_price():
    text = _fixture_text()
    rate = parse_pkr_usd_rate(text)
    assert rate == Decimal("278.2538")
    assert rate != Decimal("100.2842")


def test_parse_sbp_macro_from_fixture():
    parsed = parse_sbp_macro_from_text(_fixture_text())
    assert parsed["sbp_policy_rate"] == Decimal("11.50")
    assert parsed["pkr_usd"] == Decimal("278.2538")


def test_validate_policy_rate_bounds():
    assert validate_policy_rate(Decimal("11.5"))
    assert not validate_policy_rate(Decimal("4.9"))
    assert not validate_policy_rate(Decimal("30.1"))


def test_validate_pkr_usd_bounds():
    assert validate_pkr_usd(Decimal("278.25"))
    assert not validate_pkr_usd(Decimal("100.28"))
    assert not validate_pkr_usd(Decimal("149.99"))
    assert not validate_pkr_usd(Decimal("400.01"))
