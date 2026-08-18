import asyncio
import json
from datetime import UTC, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from backend.config import settings
from backend.models.scraper_run import ScraperRun
from backend.models.ticker import Ticker
from scrapers.psx.client import PsxClient, parse_company_equity, structure_hash
from scrapers.psx.schemas import parse_symbols_json


def get_sync_session() -> Session:
    engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
    factory = sessionmaker(bind=engine)
    return factory()


def record_scraper_run(
    session: Session,
    scraper_name: str,
    *,
    success: bool,
    records: int = 0,
    error: str | None = None,
    structure_hash_value: str | None = None,
) -> None:
    now = datetime.now(UTC)
    session.add(
        ScraperRun(
            scraper_name=scraper_name,
            last_success_at=now if success else None,
            last_run_at=now,
            records_ingested=records,
            error_message=error,
            structure_hash=structure_hash_value,
        )
    )


async def fetch_symbol_universe() -> tuple[list, str]:
    client = PsxClient()
    raw = await client.fetch_json("/symbols")
    content = json.dumps(raw, sort_keys=True)
    return raw, structure_hash(content)


async def enrich_ticker_metadata(symbol: str) -> dict:
    client = PsxClient()
    html = await client.fetch_text(f"/company/{symbol}")
    return parse_company_equity(html)


def upsert_tickers(session: Session, records: list) -> int:
    count = 0
    for record in records:
        values = {
            "symbol": record.symbol,
            "name": record.name,
            "sector": record.sector,
            "board": record.board,
            "isin": record.isin,
            "shares_outstanding": record.shares_outstanding,
            "is_debt": record.is_debt,
            "is_etf": record.is_etf,
            "is_active": True,
            "updated_at": datetime.now(UTC),
        }
        stmt = insert(Ticker).values(**values)
        update_fields = {
            "name": record.name,
            "sector": record.sector,
            "board": record.board,
            "isin": record.isin,
            "is_debt": record.is_debt,
            "is_etf": record.is_etf,
            "is_active": True,
            "updated_at": datetime.now(UTC),
        }
        if record.shares_outstanding:
            update_fields["shares_outstanding"] = record.shares_outstanding
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol"],
            set_=update_fields,
        )
        session.execute(stmt)
        count += 1
    session.commit()
    return count


async def scrape_and_store_tickers(enrich_top: int | None = None) -> dict:
    session = get_sync_session()
    try:
        raw, page_hash = await fetch_symbol_universe()
        last_run = session.scalar(
            select(ScraperRun)
            .where(ScraperRun.scraper_name == "psx_tickers")
            .order_by(ScraperRun.last_run_at.desc())
            .limit(1)
        )
        if last_run and last_run.structure_hash and last_run.structure_hash != page_hash:
            record_scraper_run(
                session,
                "psx_tickers",
                success=False,
                error="PSX symbols page structure changed",
                structure_hash_value=page_hash,
            )
            session.commit()

        records = parse_symbols_json(raw)
        equity_records = [r for r in records if not r.is_debt]
        enrich_limit = enrich_top if enrich_top is not None else len(equity_records)

        for record in equity_records[:enrich_limit]:
            try:
                meta = await enrich_ticker_metadata(record.symbol)
                if meta.get("sector"):
                    record.sector = meta["sector"]
                if meta.get("shares_outstanding"):
                    record.shares_outstanding = meta["shares_outstanding"]
                await asyncio.sleep(0.3)
            except Exception:
                continue

        count = upsert_tickers(session, equity_records)
        record_scraper_run(
            session,
            "psx_tickers",
            success=True,
            records=count,
            structure_hash_value=page_hash,
        )
        session.commit()
        return {"ingested": count, "total_symbols": len(equity_records)}
    except Exception as exc:
        session.rollback()
        record_scraper_run(session, "psx_tickers", success=False, error=str(exc))
        session.commit()
        raise
    finally:
        session.close()


def run_scrape_tickers() -> dict:
    return asyncio.run(scrape_and_store_tickers())
