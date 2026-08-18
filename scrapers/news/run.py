"""News ingestion orchestration."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from scrapers.news.base import ingest_article, load_alias_map
from scrapers.news.profit import fetch_profit_articles
from scrapers.news.psx_press import announcements_as_press_releases
from scrapers.news.rss import fetch_all_rss
from scrapers.psx.announcements import get_sync_session, record_scraper_run


async def _scrape_rss_async(sources: list[str] | None = None) -> list:
    return await fetch_all_rss(sources)


def run_scrape_news_rss(sources: list[str] | None = None) -> dict:
    session = get_sync_session()
    try:
        articles = asyncio.run(_scrape_rss_async(sources))
        alias_map = load_alias_map(session)
        ingested = linked = 0
        for article in articles:
            aid, links = ingest_article(session, article, alias_map)
            if aid:
                ingested += 1
                linked += links
        record_scraper_run(session, "scrape_news_rss", success=True, records=ingested)
        session.commit()
        return {"ingested": ingested, "links": linked, "fetched": len(articles)}
    except Exception as exc:
        session.rollback()
        record_scraper_run(session, "scrape_news_rss", success=False, error=str(exc)[:500])
        session.commit()
        raise
    finally:
        session.close()


def run_scrape_news_playwright(limit: int = 20) -> dict:
    session = get_sync_session()
    try:
        articles = asyncio.run(fetch_profit_articles(limit=limit))
        press = announcements_as_press_releases(session, limit=limit)
        articles.extend(press)
        alias_map = load_alias_map(session)
        ingested = linked = 0
        for article in articles:
            aid, links = ingest_article(session, article, alias_map)
            if aid:
                ingested += 1
                linked += links
        record_scraper_run(session, "scrape_news_playwright", success=True, records=ingested)
        session.commit()
        return {"ingested": ingested, "links": linked, "fetched": len(articles)}
    except Exception as exc:
        session.rollback()
        record_scraper_run(
            session, "scrape_news_playwright", success=False, error=str(exc)[:500]
        )
        session.commit()
        raise
    finally:
        session.close()


def run_backfill_news(days: int = 30, sources: list[str] | None = None) -> dict:
    """Backfill recent RSS articles (RSS feeds typically expose last N items)."""
    cutoff = datetime.now(UTC) - timedelta(days=days)
    session = get_sync_session()
    try:
        articles = asyncio.run(_scrape_rss_async(sources))
        articles = [a for a in articles if a.published_at >= cutoff]
        alias_map = load_alias_map(session)
        ingested = 0
        for article in articles:
            aid, _ = ingest_article(session, article, alias_map)
            if aid:
                ingested += 1
        record_scraper_run(session, "backfill_news", success=True, records=ingested)
        session.commit()
        return {"ingested": ingested, "fetched": len(articles)}
    except Exception as exc:
        session.rollback()
        record_scraper_run(session, "backfill_news", success=False, error=str(exc)[:500])
        session.commit()
        raise
    finally:
        session.close()
