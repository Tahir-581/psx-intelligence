import asyncio
import json
from datetime import UTC, datetime

import redis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.config import settings
from backend.models.scraper_run import ScraperRun
from scrapers.psx.client import PsxClient, is_market_open, parse_market_watch, structure_hash
from scrapers.psx.schemas import LtpRecord


def get_redis() -> redis.Redis:
    return redis.from_url(settings.redis_url, decode_responses=True)


def record_scraper_run(success: bool, records: int = 0, error: str | None = None) -> None:
    engine = create_engine(settings.database_url_sync)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        now = datetime.now(UTC)
        session.add(
            ScraperRun(
                scraper_name="psx_ltp",
                last_success_at=now if success else None,
                last_run_at=now,
                records_ingested=records,
                error_message=error,
            )
        )
        session.commit()


def publish_ltp(redis_client: redis.Redis, record: LtpRecord) -> None:
    snapshot = {
        "symbol": record.symbol,
        "ltp": record.ltp,
        "change": record.change,
        "change_pct": record.change_pct,
        "open": record.open,
        "high": record.high,
        "low": record.low,
        "volume": record.volume,
        "ldcp": record.ldcp,
        "board": record.board,
        "ts": datetime.now(UTC).isoformat(),
    }
    redis_client.setex(f"ticker:{record.symbol}:snapshot", 60, json.dumps(snapshot))
    redis_client.publish(f"prices:{record.symbol}", json.dumps(snapshot))


def refresh_symbol_whitelist(redis_client: redis.Redis, symbols: list[str]) -> None:
    pipe = redis_client.pipeline()
    pipe.delete("symbols:whitelist")
    if symbols:
        pipe.sadd("symbols:whitelist", *symbols)
    pipe.execute()


async def scrape_ltp() -> dict:
    if not is_market_open():
        return {"skipped": True, "reason": "market_closed"}

    client = PsxClient()
    redis_client = get_redis()
    try:
        html = await client.fetch_text("/market-watch")
        page_hash = structure_hash(html)
        rows = parse_market_watch(html)
        count = 0
        symbols: list[str] = []
        for row in rows:
            try:
                record = LtpRecord(
                    symbol=row["symbol"],
                    ltp=row["close"],
                    change=row["change"],
                    change_pct=row["change_pct"],
                    open=row["open"],
                    high=row["high"],
                    low=row["low"],
                    volume=row["volume"],
                    ldcp=row["ldcp"],
                    board=row["board"],
                )
                publish_ltp(redis_client, record)
                symbols.append(record.symbol)
                count += 1
            except Exception:
                continue
        refresh_symbol_whitelist(redis_client, symbols)
        record_scraper_run(success=True, records=count)
        return {"ingested": count, "structure_hash": page_hash}
    except Exception as exc:
        record_scraper_run(success=False, error=str(exc))
        raise
    finally:
        redis_client.close()


def run_scrape_ltp() -> dict:
    return asyncio.run(scrape_ltp())
