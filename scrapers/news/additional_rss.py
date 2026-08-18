"""RSS/HTML news scrapers for additional Pakistani sources."""

from __future__ import annotations

import feedparser

SOURCES = {
    "express_tribune": "https://tribune.com.pk/feed/business",
    "pakistan_today": "https://www.pakistantoday.com.pk/feed/",
}


def fetch_rss_entries(source: str, limit: int = 30) -> list[dict]:
    url = SOURCES.get(source)
    if not url:
        return []
    try:
        feed = feedparser.parse(url)
    except Exception:
        return []
    entries = []
    for entry in feed.entries[:limit]:
        entries.append(
            {
                "source": source,
                "headline": entry.get("title", ""),
                "source_url": entry.get("link", ""),
                "published_at": entry.get("published"),
                "excerpt": entry.get("summary", "")[:500],
            }
        )
    return entries
