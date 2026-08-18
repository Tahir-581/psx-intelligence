import asyncio
from datetime import UTC, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from backend.config import settings
from backend.models.announcement import Announcement
from backend.models.scraper_run import ScraperRun
from backend.models.ticker import Ticker
from scrapers.psx.client import PsxClient, is_market_open, structure_hash
from scrapers.psx.schemas import AnnouncementRecord, parse_announcements_from_company_html


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


def upsert_announcements(session: Session, records: list[AnnouncementRecord]) -> int:
    if not records:
        return 0
    rows = [
        {
            "symbol": r.symbol,
            "published_at": r.published_at,
            "title": r.title,
            "category": r.category,
            "pdf_url": r.pdf_url,
            "source_url": r.source_url,
            "body_text": r.body_text,
        }
        for r in records
    ]
    stmt = insert(Announcement).values(rows)
    stmt = stmt.on_conflict_do_nothing(constraint="uq_announcements_symbol_pub_title")
    result = session.execute(stmt)
    session.commit()
    return result.rowcount or 0


async def scrape_symbol_announcements(client: PsxClient, symbol: str) -> list[AnnouncementRecord]:
    html = await client.fetch_text(f"/company/{symbol}")
    return parse_announcements_from_company_html(html, symbol, client.base_url)


async def scrape_announcements(symbols: list[str] | None = None) -> dict:
    if symbols is None and not is_market_open():
        return {"ingested": 0, "symbols_processed": 0, "skipped": "market_closed"}

    session = get_sync_session()
    client = PsxClient()
    try:
        if symbols is None:
            symbols = list(
                session.scalars(
                    select(Ticker.symbol).where(
                        Ticker.is_active.is_(True), Ticker.is_debt.is_(False)
                    )
                )
            )
        total = 0
        page_hash = None
        for symbol in symbols:
            try:
                html = await client.fetch_text(f"/company/{symbol}")
                page_hash = structure_hash(html)
                records = parse_announcements_from_company_html(html, symbol, client.base_url)
                total += upsert_announcements(session, records)
                await asyncio.sleep(settings.psx_request_delay_seconds)
            except Exception:
                continue
        record_scraper_run(
            session,
            "psx_announcements",
            success=True,
            records=total,
            structure_hash_value=page_hash,
        )
        session.commit()
        return {"ingested": total, "symbols_processed": len(symbols), "symbols": symbols if total > 0 else []}
    except Exception as exc:
        session.rollback()
        record_scraper_run(
            session, "psx_announcements", success=False, error=str(exc)
        )
        session.commit()
        raise
    finally:
        session.close()


async def backfill_symbol_announcements(symbol: str) -> int:
    session = get_sync_session()
    client = PsxClient()
    try:
        html = await client.fetch_text(f"/company/{symbol}")
        records = parse_announcements_from_company_html(html, symbol, client.base_url)
        count = upsert_announcements(session, records)
        record_scraper_run(
            session,
            f"psx_announcements_backfill_{symbol}",
            success=True,
            records=count,
        )
        session.commit()
        return count
    except Exception as exc:
        session.rollback()
        record_scraper_run(
            session,
            f"psx_announcements_backfill_{symbol}",
            success=False,
            error=str(exc),
        )
        session.commit()
        raise
    finally:
        session.close()


def run_scrape_announcements(symbols: list[str] | None = None) -> dict:
    return asyncio.run(scrape_announcements(symbols))


def run_backfill_symbol_announcements(symbol: str) -> int:
    return asyncio.run(backfill_symbol_announcements(symbol))
