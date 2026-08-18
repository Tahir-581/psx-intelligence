"""Macro economic data scrapers with seed fallback."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.dialects.postgresql import insert

from backend.models.macro_series import MacroSeries
from scrapers.psx.announcements import get_sync_session, record_scraper_run

SBP_ECODATA_URL = "https://www.sbp.org.pk/ecodata/index2.asp"

POLICY_RATE_MIN = Decimal("5")
POLICY_RATE_MAX = Decimal("30")
PKR_USD_MIN = Decimal("150")
PKR_USD_MAX = Decimal("400")

# Curated fallback seed data (updated periodically via scripts/seed_macro.py)
SEED_MACRO: list[dict] = [
    {"time": "2024-01-01T00:00:00+00:00", "series_code": "sbp_policy_rate", "value": "22.0", "unit": "percent"},
    {"time": "2024-06-01T00:00:00+00:00", "series_code": "sbp_policy_rate", "value": "20.5", "unit": "percent"},
    {"time": "2026-06-01T00:00:00+00:00", "series_code": "sbp_policy_rate", "value": "11.5", "unit": "percent"},
    {"time": "2024-01-01T00:00:00+00:00", "series_code": "cpi_yoy", "value": "28.3", "unit": "percent"},
    {"time": "2024-06-01T00:00:00+00:00", "series_code": "cpi_yoy", "value": "12.6", "unit": "percent"},
    {"time": "2024-01-02T00:00:00+00:00", "series_code": "pkr_usd", "value": "279.5", "unit": "PKR/USD"},
    {"time": "2024-06-01T00:00:00+00:00", "series_code": "pkr_usd", "value": "278.2", "unit": "PKR/USD"},
    {"time": "2026-06-01T00:00:00+00:00", "series_code": "pkr_usd", "value": "278.4", "unit": "PKR/USD"},
    {"time": "2024-06-01T00:00:00+00:00", "series_code": "fx_reserves_usd", "value": "9000000000", "unit": "USD"},
    {"time": "2024-06-01T00:00:00+00:00", "series_code": "tbill_3m", "value": "20.1", "unit": "percent"},
]


def parse_sbp_policy_rate(text: str) -> Decimal | None:
    """Extract SBP policy rate from ecodata page text."""
    patterns = [
        r"SBP\s+Policy\s+Rat\s*e\s+(\d+\.\d+)\s*%\s*p\.a\.",
        r"SBP Policy Rate\s*(\d+\.\d+)\s*%",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return Decimal(match.group(1))
    return None


def parse_pkr_usd_rate(text: str) -> Decimal | None:
    """Extract PKR/USD weighted average rate from ecodata page text."""
    patterns = [
        r"(\d{3}\.\d{3,4})\s*Weighted Average Rate",
        r"M2M Revaluation Rate\s*(\d{3}\.\d{3,4})",
        r"Exchange Rates.*?(\d{3}\.\d{3,4})\s*Weighted Average Rate",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            value = Decimal(match.group(1))
            if PKR_USD_MIN <= value <= PKR_USD_MAX:
                return value

    exchange_section = re.search(r"Exchange Rates(.*?)(?:Foreign Investment|Pakistan's Debt)", text, re.DOTALL | re.IGNORECASE)
    if exchange_section:
        for candidate in re.findall(r"\b(\d{3}\.\d{3,4})\b", exchange_section.group(1)):
            value = Decimal(candidate)
            if PKR_USD_MIN <= value <= PKR_USD_MAX:
                return value
    return None


def validate_policy_rate(value: Decimal) -> bool:
    return POLICY_RATE_MIN <= value <= POLICY_RATE_MAX


def validate_pkr_usd(value: Decimal) -> bool:
    return PKR_USD_MIN <= value <= PKR_USD_MAX


def parse_sbp_macro_from_text(text: str) -> dict[str, Decimal]:
    """Parse live SBP policy rate and PKR/USD from page text."""
    parsed: dict[str, Decimal] = {}

    policy_rate = parse_sbp_policy_rate(text)
    if policy_rate is not None and validate_policy_rate(policy_rate):
        parsed["sbp_policy_rate"] = policy_rate

    pkr_usd = parse_pkr_usd_rate(text)
    if pkr_usd is not None and validate_pkr_usd(pkr_usd):
        parsed["pkr_usd"] = pkr_usd

    return parsed


def macro_rows_from_parsed(parsed: dict[str, Decimal], *, at: datetime | None = None) -> list[dict]:
    """Build macro_series rows from parsed values."""
    now = at or datetime.now(UTC)
    units = {
        "sbp_policy_rate": "percent",
        "pkr_usd": "PKR/USD",
    }
    return [
        {
            "time": now,
            "series_code": series_code,
            "value": value,
            "unit": units[series_code],
        }
        for series_code, value in parsed.items()
    ]


async def fetch_sbp_macro() -> list[dict]:
    """Scrape SBP policy rate and PKR/USD from the ecodata index page."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(SBP_ECODATA_URL, timeout=30.0, follow_redirects=True)
            if resp.status_code != 200:
                return []
            soup = BeautifulSoup(resp.text, "lxml")
            text = soup.get_text(" ", strip=True)
            parsed = parse_sbp_macro_from_text(text)
            return macro_rows_from_parsed(parsed)
    except Exception:
        return []


def upsert_macro_rows(session, rows: list[dict]) -> int:
    if not rows:
        return 0
    stmt = insert(MacroSeries).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["time", "series_code"],
        set_={"value": stmt.excluded.value, "unit": stmt.excluded.unit},
    )
    result = session.execute(stmt)
    session.commit()
    return result.rowcount or len(rows)


def seed_macro_data(session, *, series_codes: set[str] | None = None) -> int:
    rows = []
    for item in SEED_MACRO:
        if series_codes is not None and item["series_code"] not in series_codes:
            continue
        rows.append(
            {
                "time": datetime.fromisoformat(item["time"]),
                "series_code": item["series_code"],
                "value": Decimal(item["value"]),
                "unit": item["unit"],
            }
        )
    return upsert_macro_rows(session, rows)


def run_scrape_macro() -> dict:
    import asyncio

    session = get_sync_session()
    try:
        scraped = asyncio.run(fetch_sbp_macro())
        scraped_codes = {row["series_code"] for row in scraped}
        ingested = upsert_macro_rows(session, scraped)
        ingested += seed_macro_data(session)

        record_scraper_run(session, "scrape_macro", success=True, records=ingested)
        session.commit()
        return {"ingested": ingested, "scraped_series": sorted(scraped_codes)}
    except Exception as exc:
        session.rollback()
        record_scraper_run(session, "scrape_macro", success=False, error=str(exc)[:500])
        session.commit()
        raise
    finally:
        session.close()
