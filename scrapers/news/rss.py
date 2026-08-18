"""RSS news scrapers for Business Recorder and Dawn."""

from __future__ import annotations

from datetime import UTC, datetime

import feedparser
import httpx
from dateutil import parser as date_parser

from scrapers.news.base import RawArticle

RSS_SOURCES: dict[str, str] = {
    "business_recorder": "https://www.brecorder.com/feeds/business",
    "dawn": "https://www.dawn.com/feeds/business",
}


def parse_feed_entries(source: str, feed_url: str, xml: str) -> list[RawArticle]:
    parsed = feedparser.parse(xml)
    articles: list[RawArticle] = []
    for entry in parsed.entries:
        link = entry.get("link")
        title = entry.get("title")
        if not link or not title:
            continue
        published = entry.get("published") or entry.get("updated")
        if published:
            try:
                published_at = date_parser.parse(published)
                if published_at.tzinfo is None:
                    published_at = published_at.replace(tzinfo=UTC)
            except (ValueError, TypeError):
                published_at = datetime.now(UTC)
        else:
            published_at = datetime.now(UTC)
        author = entry.get("author")
        summary = entry.get("summary") or entry.get("description")
        articles.append(
            RawArticle(
                source=source,
                headline=title,
                source_url=link,
                published_at=published_at,
                author=author,
                html_or_text=summary,
            )
        )
    return articles


async def fetch_rss_source(client: httpx.AsyncClient, source: str) -> list[RawArticle]:
    url = RSS_SOURCES.get(source)
    if not url:
        return []
    resp = await client.get(url, timeout=30.0, follow_redirects=True)
    resp.raise_for_status()
    return parse_feed_entries(source, url, resp.text)


async def fetch_all_rss(sources: list[str] | None = None) -> list[RawArticle]:
    selected = sources or list(RSS_SOURCES.keys())
    articles: list[RawArticle] = []
    async with httpx.AsyncClient() as client:
        for source in selected:
            try:
                articles.extend(await fetch_rss_source(client, source))
            except Exception:
                continue
    return articles
