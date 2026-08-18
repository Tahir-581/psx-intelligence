from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scrapers.psx.eod_prices import (
    INDEX_SYMBOLS,
    _scrape_indices_with_retry,
    scrape_all_eod,
)


@pytest.mark.asyncio
async def test_scrape_indices_with_retry_succeeds_after_transient_failure() -> None:
    session = MagicMock()
    client = MagicMock()
    failed_symbols: list[str] = []
    attempts: dict[str, int] = {}

    async def ingest(_session, _client, symbol: str) -> int:
        attempts[symbol] = attempts.get(symbol, 0) + 1
        if symbol == "KSE100" and attempts[symbol] == 1:
            raise ConnectionError("transient")
        return 1

    with patch("scrapers.psx.eod_prices._ingest_latest_eod", side_effect=ingest):
        with patch("scrapers.psx.eod_prices.asyncio.sleep", new_callable=AsyncMock):
            total = await _scrape_indices_with_retry(session, client, failed_symbols)

    assert total == len(INDEX_SYMBOLS)
    assert failed_symbols == []


@pytest.mark.asyncio
async def test_scrape_all_eod_reports_index_failures() -> None:
    session = MagicMock()
    client = MagicMock()

    async def ingest(_session, _client, symbol: str) -> int:
        if symbol in INDEX_SYMBOLS:
            raise RuntimeError(f"fail {symbol}")
        return 1

    with patch("scrapers.psx.eod_prices.get_sync_session", return_value=session):
        with patch("scrapers.psx.eod_prices.PsxClient", return_value=client):
            with patch("scrapers.psx.eod_prices._ingest_latest_eod", side_effect=ingest):
                with patch("scrapers.psx.eod_prices._scrape_symbol_batch", return_value=2):
                    with patch("scrapers.psx.eod_prices.record_scraper_run") as record_run:
                        with patch("scrapers.psx.eod_prices._invalidate_price_caches") as invalidate:
                            with patch("scrapers.psx.eod_prices.asyncio.sleep", new_callable=AsyncMock):
                                result = await scrape_all_eod(["OGDC"])

    assert result["index_failed"] == INDEX_SYMBOLS
    assert set(result["failed_symbols"]) == set(INDEX_SYMBOLS)
    record_run.assert_called_once()
    assert record_run.call_args.kwargs["success"] is False
    assert "Index symbols failed" in record_run.call_args.kwargs["error"]
    invalidate.assert_not_called()


@pytest.mark.asyncio
async def test_scrape_all_eod_invalidates_cache_on_success() -> None:
    session = MagicMock()

    with patch("scrapers.psx.eod_prices.get_sync_session", return_value=session):
        with patch("scrapers.psx.eod_prices.PsxClient"):
            with patch("scrapers.psx.eod_prices._scrape_symbol_batch", return_value=1):
                with patch("scrapers.psx.eod_prices._scrape_indices_with_retry", return_value=3):
                    with patch("scrapers.psx.eod_prices.record_scraper_run"):
                        with patch("scrapers.psx.eod_prices._invalidate_price_caches") as invalidate:
                            result = await scrape_all_eod(["OGDC"])

    assert result["index_failed"] == []
    invalidate.assert_called_once()
