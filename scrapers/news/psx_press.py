"""Ingest PSX press releases from announcements table."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.announcement import Announcement
from scrapers.news.base import RawArticle


def announcements_as_press_releases(session: Session, limit: int = 50) -> list[RawArticle]:
    rows = session.scalars(
        select(Announcement)
        .where(Announcement.title.ilike("%press release%"))
        .order_by(Announcement.published_at.desc())
        .limit(limit)
    ).all()
    articles: list[RawArticle] = []
    for row in rows:
        articles.append(
            RawArticle(
                source="psx_press",
                headline=row.title,
                source_url=row.source_url or row.pdf_url or f"psx://announcement/{row.id}",
                published_at=row.published_at or datetime.now(UTC),
                html_or_text=row.body_text,
            )
        )
    return articles
