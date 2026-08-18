"""Profit.com.pk news scraper (httpx + BeautifulSoup)."""

from __future__ import annotations

import re
from datetime import UTC, datetime

import httpx
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from scrapers.news.base import RawArticle

PROFIT_LISTING_URL = "https://profit.pakistantoday.com.pk/"


async def fetch_profit_articles(limit: int = 20) -> list[RawArticle]:
    articles: list[RawArticle] = []
    async with httpx.AsyncClient() as client:
        resp = await client.get(PROFIT_LISTING_URL, timeout=30.0, follow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        links = soup.select("a[href*='/']")
        seen: set[str] = set()
        for a in links:
            href = a.get("href", "")
            title = a.get_text(strip=True)
            if not title or len(title) < 20:
                continue
            if not href.startswith("http"):
                href = f"https://profit.pakistantoday.com.pk{href}" if href.startswith("/") else href
            if "profit.pakistantoday" not in href or href in seen:
                continue
            seen.add(href)
            published_at = datetime.now(UTC)
            parent = a.find_parent(["article", "div"])
            date_el = parent.find("time") if parent else None
            if date_el and date_el.get("datetime"):
                try:
                    published_at = date_parser.parse(date_el["datetime"])
                    if published_at.tzinfo is None:
                        published_at = published_at.replace(tzinfo=UTC)
                except (ValueError, TypeError):
                    pass
            html = None
            try:
                art_resp = await client.get(href, timeout=20.0, follow_redirects=True)
                if art_resp.status_code == 200:
                    html = art_resp.text
            except Exception:
                pass
            articles.append(
                RawArticle(
                    source="profit",
                    headline=title,
                    source_url=href,
                    published_at=published_at,
                    html_or_text=html,
                )
            )
            if len(articles) >= limit:
                break
    return articles
