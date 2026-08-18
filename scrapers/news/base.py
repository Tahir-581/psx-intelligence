"""Shared news ingestion utilities."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime

import trafilatura
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from backend.models.news_article import NewsArticle
from backend.models.news_article_ticker import NewsArticleTicker
from backend.models.ticker import Ticker
from nlp.entity_linker import build_alias_map, link_tickers
from nlp.topic_tagger import tag_topic


@dataclass
class RawArticle:
    source: str
    headline: str
    source_url: str
    published_at: datetime
    author: str | None = None
    html_or_text: str | None = None


def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


def make_excerpt(html_or_text: str | None, headline: str, max_len: int = 500) -> str:
    if html_or_text:
        extracted = trafilatura.extract(
            html_or_text,
            include_comments=False,
            include_tables=False,
            favor_precision=True,
        )
        if extracted:
            text = extracted
        else:
            text = re.sub(r"<[^>]+>", " ", html_or_text)
    else:
        text = headline
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len]


def load_alias_map(session: Session) -> dict[str, str]:
    rows = session.execute(select(Ticker.symbol, Ticker.name).where(Ticker.is_active.is_(True))).all()
    symbols = [r[0] for r in rows]
    names = [r[1] for r in rows]
    return build_alias_map(symbols, names)


def upsert_article(session: Session, article: RawArticle) -> int | None:
    excerpt = make_excerpt(article.html_or_text, article.headline)
    topic = tag_topic(f"{article.headline} {excerpt}")
    external_id = url_hash(article.source_url)
    row = {
        "source": article.source,
        "external_id": external_id,
        "headline": article.headline[:1000],
        "published_at": article.published_at,
        "author": article.author,
        "source_url": article.source_url,
        "excerpt": excerpt,
        "topic_tag": topic,
    }
    stmt = insert(NewsArticle).values(row)
    stmt = stmt.on_conflict_do_nothing(constraint="uq_news_articles_source_url")
    result = session.execute(stmt)
    session.commit()
    if not result.rowcount:
        existing = session.scalar(
            select(NewsArticle.id).where(NewsArticle.source_url == article.source_url)
        )
        return existing
    return session.scalar(select(NewsArticle.id).where(NewsArticle.source_url == article.source_url))


def link_article_tickers(
    session: Session,
    article_id: int,
    text: str,
    alias_map: dict[str, str],
) -> int:
    links = link_tickers(text, alias_map)
    count = 0
    for link in links:
        stmt = insert(NewsArticleTicker).values(
            {
                "article_id": article_id,
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


def ingest_article(
    session: Session,
    article: RawArticle,
    alias_map: dict[str, str],
) -> tuple[int | None, int]:
    article_id = upsert_article(session, article)
    if not article_id:
        return None, 0
    excerpt = make_excerpt(article.html_or_text, article.headline)
    linked = link_article_tickers(
        session,
        article_id,
        f"{article.headline} {excerpt}",
        alias_map,
    )
    return article_id, linked
