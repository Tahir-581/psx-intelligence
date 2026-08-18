"""Shared social post ingestion utilities."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from backend.models.social_post import SocialPost
from backend.models.social_post_ticker import SocialPostTicker
from backend.models.ticker import Ticker
from nlp.entity_linker import build_alias_map, link_tickers
from scrapers.news.base import load_alias_map
from scrapers.social.schemas import SocialPostRecord


def upsert_social_post(session: Session, record: SocialPostRecord) -> int | None:
    row = {
        "source": record.source,
        "external_id": record.external_id,
        "symbol": record.symbol,
        "author_handle": record.author_handle,
        "author_followers": record.author_followers,
        "posted_at": record.posted_at,
        "text": record.text,
        "engagement_json": record.engagement_json,
        "url": record.url,
    }
    stmt = insert(SocialPost).values(row)
    stmt = stmt.on_conflict_do_nothing(constraint="uq_social_posts_source_external")
    result = session.execute(stmt)
    session.commit()
    if not result.rowcount:
        existing = session.scalar(
            select(SocialPost.id).where(
                SocialPost.source == record.source,
                SocialPost.external_id == record.external_id,
            )
        )
        return existing
    return session.scalar(
        select(SocialPost.id).where(
            SocialPost.source == record.source,
            SocialPost.external_id == record.external_id,
        )
    )


def link_post_tickers(
    session: Session,
    post_id: int,
    text: str,
    alias_map: dict[str, str],
) -> int:
    links = link_tickers(text, alias_map)
    count = 0
    for link in links:
        stmt = insert(SocialPostTicker).values(
            {
                "post_id": post_id,
                "symbol": link.symbol,
                "link_confidence": link.confidence,
            }
        )
        stmt = stmt.on_conflict_do_nothing()
        result = session.execute(stmt)
        if result.rowcount:
            count += 1
    session.commit()
    return count


def ingest_social_post(
    session: Session,
    record: SocialPostRecord,
    alias_map: dict[str, str],
) -> tuple[int | None, int]:
    post_id = upsert_social_post(session, record)
    if not post_id:
        return None, 0
    linked = link_post_tickers(session, post_id, record.text, alias_map)
    return post_id, linked


__all__ = ["load_alias_map", "build_alias_map", "ingest_social_post", "upsert_social_post"]
