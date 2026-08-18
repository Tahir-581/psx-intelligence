"""Social scraper orchestration."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from scrapers.psx.announcements import record_scraper_run
from scrapers.social.reddit import run_scrape_reddit
from scrapers.social.telegram import run_scrape_telegram
from scrapers.social.twitter import run_scrape_twitter

logger = logging.getLogger(__name__)


def run_twitter_scrape(session: Session, *, limit_symbols: int | None = None) -> dict:
    scraper_name = "scrape_twitter"
    try:
        result = run_scrape_twitter(limit_symbols=limit_symbols)
        record_scraper_run(
            session,
            scraper_name,
            success=True,
            records=result.get("ingested", 0),
        )
        session.commit()
        return result
    except Exception as exc:
        session.rollback()
        record_scraper_run(session, scraper_name, success=False, error=str(exc)[:500])
        session.commit()
        raise


def run_twitter_scrape_standalone(limit_symbols: int | None = None) -> dict:
    from backend.config import settings
    from sqlalchemy import create_engine

    engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
    with Session(engine) as session:
        return run_twitter_scrape(session, limit_symbols=limit_symbols)


def run_telegram_scrape_standalone() -> dict:
    from backend.config import settings
    from sqlalchemy import create_engine

    engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
    with Session(engine) as session:
        try:
            result = run_scrape_telegram()
            record_scraper_run(
                session, "scrape_telegram", success=True, records=result.get("ingested", 0)
            )
            session.commit()
            return result
        except Exception as exc:
            session.rollback()
            record_scraper_run(session, "scrape_telegram", success=False, error=str(exc)[:500])
            session.commit()
            raise


def run_reddit_scrape_standalone() -> dict:
    from backend.config import settings
    from sqlalchemy import create_engine

    engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
    with Session(engine) as session:
        try:
            result = run_scrape_reddit()
            record_scraper_run(
                session, "scrape_reddit", success=True, records=result.get("ingested", 0)
            )
            session.commit()
            return result
        except Exception as exc:
            session.rollback()
            record_scraper_run(session, "scrape_reddit", success=False, error=str(exc)[:500])
            session.commit()
            raise
