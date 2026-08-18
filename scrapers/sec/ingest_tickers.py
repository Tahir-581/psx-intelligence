"""Seed sec_cusip_ticker_map and backfill sec_holdings tickers."""

from __future__ import annotations

import json
import logging

import httpx
from sqlalchemy import create_engine, text

from backend.config import settings
from scrapers.sec.ingest_utils import pad_cik

logger = logging.getLogger(__name__)

KNOWN_CUSIPS: dict[str, dict[str, str]] = {
    "78462F103": {"ticker": "SPY", "name": "SPDR S&P 500 ETF"},
    "037833100": {"ticker": "AAPL", "name": "Apple Inc"},
    "594918104": {"ticker": "MSFT", "name": "Microsoft Corp"},
    "67066G104": {"ticker": "NVDA", "name": "NVIDIA Corp"},
    "023135106": {"ticker": "AMZN", "name": "Amazon.com Inc"},
    "30303M102": {"ticker": "META", "name": "Meta Platforms Inc"},
    "02079K305": {"ticker": "GOOGL", "name": "Alphabet Inc"},
    "88160R101": {"ticker": "TSLA", "name": "Tesla Inc"},
    "46625H100": {"ticker": "JPM", "name": "JPMorgan Chase & Co"},
    "92826C839": {"ticker": "V", "name": "Visa Inc"},
    "084670702": {"ticker": "BRK.B", "name": "Berkshire Hathaway Inc"},
    "025816109": {"ticker": "AXP", "name": "American Express Co"},
    "949746101": {"ticker": "KO", "name": "Coca-Cola Co"},
    "742718109": {"ticker": "PG", "name": "Procter & Gamble Co"},
    "931142103": {"ticker": "WMT", "name": "Walmart Inc"},
    "459200101": {"ticker": "IBM", "name": "IBM Corp"},
    "438516106": {"ticker": "HON", "name": "Honeywell International"},
}


def run_ingest_tickers() -> dict:
    engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
    upserted = 0
    logger.info("Upserting %s known CUSIP mappings...", len(KNOWN_CUSIPS))
    with engine.begin() as conn:
        for cusip, info in KNOWN_CUSIPS.items():
            conn.execute(
                text("""
                    INSERT INTO sec_cusip_ticker_map (cusip, ticker, company_name, updated_at)
                    VALUES (:cusip, :ticker, :name, NOW())
                    ON CONFLICT (cusip) DO UPDATE SET ticker = EXCLUDED.ticker,
                      company_name = EXCLUDED.company_name, updated_at = NOW()
                """),
                {"cusip": cusip, "ticker": info["ticker"], "name": info["name"]},
            )
            upserted += 1

        cik_tickers = 0
        try:
            logger.info("Fetching company_tickers.json from SEC...")
            with httpx.Client(timeout=60.0) as client:
                res = client.get(
                    "https://www.sec.gov/files/company_tickers.json",
                    headers={"User-Agent": settings.sec_user_agent},
                )
                if res.status_code == 200:
                    data = res.json()
                    for entry in data.values():
                        ticker = entry.get("ticker")
                        if not ticker:
                            continue
                        cik = pad_cik(str(entry.get("cik_str", "")))
                        if not cik:
                            continue
                        result = conn.execute(
                            text("""
                                UPDATE sec_holdings
                                SET ticker = :ticker
                                WHERE cik = :cik AND (ticker IS NULL OR ticker = '')
                            """),
                            {"cik": cik, "ticker": ticker},
                        )
                        cik_tickers += result.rowcount or 0
        except Exception as exc:
            logger.warning("Could not fetch company_tickers.json: %s", exc)

        logger.info("Backfilling tickers on holdings from CUSIP map...")
        conn.execute(
            text("""
                UPDATE sec_holdings h SET ticker = m.ticker
                FROM sec_cusip_ticker_map m
                WHERE h.cusip = m.cusip AND (h.ticker IS NULL OR h.ticker = '')
            """)
        )

    logger.info(
        "Ticker ingest complete: %s known CUSIPs, %s CIK ticker updates",
        upserted,
        cik_tickers,
    )
    return {"status": "success", "knownCusips": upserted, "cikTickerUpdates": cik_tickers}
