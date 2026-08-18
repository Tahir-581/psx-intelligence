import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from backend.config import settings
from backend.models.price import Price
from backend.models.scraper_run import ScraperRun
from backend.models.ticker import Ticker
from scrapers.psx.client import PsxClient, structure_hash, unix_to_utc
from scrapers.psx.schemas import EodPriceRecord, parse_eod_rows

INDEX_SYMBOLS = ["KSE100", "KSE30", "KMI30"]
FIVE_YEARS_SECONDS = 5 * 365 * 24 * 3600
INDEX_RETRY_ATTEMPTS = 3
INDEX_RETRY_BACKOFF_SECONDS = 2.0

logger = logging.getLogger(__name__)


def get_sync_session() -> Session:
    engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
    return sessionmaker(bind=engine)()


def record_scraper_run(
    session: Session,
    scraper_name: str,
    *,
    success: bool,
    records: int = 0,
    error: str | None = None,
) -> None:
    now = datetime.now(UTC)
    session.add(
        ScraperRun(
            scraper_name=scraper_name,
            last_success_at=now if success else None,
            last_run_at=now,
            records_ingested=records,
            error_message=error,
        )
    )


def price_continuity_ok(prev_close: float | None, new_close: float) -> bool:
    if prev_close is None or prev_close == 0:
        return True
    change = abs(new_close - prev_close) / prev_close
    return change <= 0.5


def dedupe_price_records(records: list[EodPriceRecord]) -> list[EodPriceRecord]:
    """Deduplicate by (symbol, time); last row wins."""
    seen: dict[tuple[str, datetime], EodPriceRecord] = {}
    for r in records:
        seen[(r.symbol, unix_to_utc(r.time_unix))] = r
    return list(seen.values())


def upsert_prices(session: Session, records: list[EodPriceRecord]) -> int:
    if not records:
        return 0
    records = dedupe_price_records(records)
    rows = [
        {
            "time": unix_to_utc(r.time_unix),
            "symbol": r.symbol,
            "open": Decimal(str(r.open)),
            "high": Decimal(str(r.high)),
            "low": Decimal(str(r.low)),
            "close": Decimal(str(r.close)),
            "volume": r.volume,
            "value_traded": Decimal(str(r.value_traded)) if r.value_traded else None,
        }
        for r in records
    ]
    stmt = insert(Price).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["time", "symbol"],
        set_={
            "open": stmt.excluded.open,
            "high": stmt.excluded.high,
            "low": stmt.excluded.low,
            "close": stmt.excluded.close,
            "volume": stmt.excluded.volume,
            "value_traded": stmt.excluded.value_traded,
        },
    )
    session.execute(stmt)
    session.commit()
    return len(rows)


async def fetch_eod_for_symbol(client: PsxClient, symbol: str) -> list[EodPriceRecord]:
    payload = await client.fetch_json(f"/timeseries/eod/{symbol}")
    return parse_eod_rows(symbol, payload)


async def _ingest_latest_eod(session: Session, client: PsxClient, symbol: str) -> int:
    payload = await client.fetch_json(f"/timeseries/eod/{symbol}")
    records = parse_eod_rows(symbol, payload)
    return upsert_prices(session, records[:1])


async def _scrape_symbol_batch(
    session: Session,
    client: PsxClient,
    symbols: list[str],
    failed_symbols: list[str],
) -> int:
    total = 0
    for symbol in symbols:
        try:
            total += await _ingest_latest_eod(session, client, symbol)
            await asyncio.sleep(settings.psx_request_delay_seconds)
        except Exception as exc:
            logger.warning("EOD scrape failed for %s: %s", symbol, exc)
            failed_symbols.append(symbol)
    return total


async def _scrape_indices_with_retry(
    session: Session,
    client: PsxClient,
    failed_symbols: list[str],
) -> int:
    total = 0
    remaining = list(INDEX_SYMBOLS)

    for attempt in range(INDEX_RETRY_ATTEMPTS):
        if not remaining:
            break
        if attempt > 0:
            await asyncio.sleep(INDEX_RETRY_BACKOFF_SECONDS * attempt)

        still_failed: list[str] = []
        for symbol in remaining:
            try:
                total += await _ingest_latest_eod(session, client, symbol)
                if symbol in failed_symbols:
                    failed_symbols.remove(symbol)
                await asyncio.sleep(settings.psx_request_delay_seconds)
            except Exception as exc:
                logger.warning(
                    "Index EOD scrape failed for %s (attempt %d/%d): %s",
                    symbol,
                    attempt + 1,
                    INDEX_RETRY_ATTEMPTS,
                    exc,
                )
                still_failed.append(symbol)
        remaining = still_failed

    for symbol in remaining:
        if symbol not in failed_symbols:
            failed_symbols.append(symbol)

    return total


def _invalidate_price_caches() -> None:
    from backend.services.cache import flush_cache_pattern_sync

    flush_cache_pattern_sync("ticker:*:prices:*")
    flush_cache_pattern_sync("market:summary")


async def scrape_symbol_eod(symbol: str, cutoff_ts: int | None = None) -> list[EodPriceRecord]:
    client = PsxClient()
    records = await fetch_eod_for_symbol(client, symbol)
    if cutoff_ts:
        records = [r for r in records if r.time_unix >= cutoff_ts]
    if len(records) >= 2:
        latest, previous = records[0], records[1]
        if not price_continuity_ok(previous.close, latest.close):
            raise ValueError(
                f"Price continuity check failed for {symbol}: "
                f"{previous.close} -> {latest.close}"
            )
    return records


async def scrape_all_eod(symbols: list[str] | None = None) -> dict:
    session = get_sync_session()
    client = PsxClient()
    try:
        if symbols is None:
            symbols = list(
                session.scalars(
                    select(Ticker.symbol).where(Ticker.is_active.is_(True), Ticker.is_debt.is_(False))
                )
            )
        equity_symbols = [s for s in dict.fromkeys(symbols) if s not in INDEX_SYMBOLS]
        failed_symbols: list[str] = []
        total = await _scrape_symbol_batch(session, client, equity_symbols, failed_symbols)
        total += await _scrape_indices_with_retry(session, client, failed_symbols)

        index_failed = [s for s in INDEX_SYMBOLS if s in failed_symbols]
        success = len(index_failed) == 0
        error_msg = f"Index symbols failed: {', '.join(index_failed)}" if index_failed else None
        record_scraper_run(
            session,
            "psx_eod_prices",
            success=success,
            records=total,
            error=error_msg,
        )
        session.commit()
        if success:
            _invalidate_price_caches()
        return {
            "ingested": total,
            "symbols_processed": len(equity_symbols) + len(INDEX_SYMBOLS),
            "failed_symbols": failed_symbols,
            "index_failed": index_failed,
        }
    except Exception as exc:
        session.rollback()
        record_scraper_run(session, "psx_eod_prices", success=False, error=str(exc))
        session.commit()
        raise
    finally:
        session.close()


async def backfill_symbol(symbol: str, years: int = 5) -> int:
    session = get_sync_session()
    client = PsxClient()
    try:
        payload = await client.fetch_json(f"/timeseries/eod/{symbol}")
        page_hash = structure_hash(json.dumps(payload))
        cutoff = int((datetime.now(UTC) - timedelta(days=years * 365)).timestamp())
        records = [r for r in parse_eod_rows(symbol, payload) if r.time_unix >= cutoff]
        count = upsert_prices(session, records)
        record_scraper_run(session, f"psx_eod_backfill_{symbol}", success=True, records=count)
        session.commit()
        return count
    except Exception as exc:
        session.rollback()
        record_scraper_run(
            session, f"psx_eod_backfill_{symbol}", success=False, error=str(exc)
        )
        session.commit()
        raise
    finally:
        session.close()


def run_scrape_eod() -> dict:
    return asyncio.run(scrape_all_eod())


def run_backfill_symbol(symbol: str, years: int = 5) -> int:
    return asyncio.run(backfill_symbol(symbol, years))
