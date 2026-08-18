from datetime import datetime

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.news_article import NewsArticle
from backend.models.news_article_ticker import NewsArticleTicker
from backend.schemas.context import NewsItem, NewsListResponse


async def get_ticker_news(
    db: AsyncSession,
    symbol: str,
    *,
    source: str | None = None,
    topic: str | None = None,
    page: int = 1,
    page_size: int = 20,
    published_after: datetime | None = None,
    include_pro_fields: bool = False,
) -> NewsListResponse:
    query = (
        select(NewsArticle, NewsArticleTicker.link_confidence)
        .join(NewsArticleTicker, NewsArticleTicker.article_id == NewsArticle.id)
        .where(NewsArticleTicker.symbol == symbol)
    )
    if source:
        query = query.where(NewsArticle.source == source)
    if topic:
        query = query.where(NewsArticle.topic_tag == topic)
    if published_after:
        query = query.where(NewsArticle.published_at >= published_after)
    count_q = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_q) or 0
    result = await db.execute(
        query.order_by(desc(NewsArticle.published_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = []
    for article, confidence in result.all():
        ai_summary = None
        sentiment_badge = None
        if include_pro_fields:
            from backend.services.intelligence import (
                get_article_ai_summary,
                get_article_sentiment_badge,
            )

            ai_summary = await get_article_ai_summary(db, article.id)
            sentiment_badge = get_article_sentiment_badge(article.id)
        items.append(
            NewsItem(
                id=article.id,
                source=article.source,
                headline=article.headline,
                published_at=article.published_at,
                author=article.author,
                source_url=article.source_url,
                excerpt=article.excerpt,
                topic_tag=article.topic_tag,
                link_confidence=float(confidence) if confidence else None,
                ai_summary=ai_summary,
                sentiment_badge=sentiment_badge,
            )
        )
    return NewsListResponse(items=items, total=total, page=page, page_size=page_size)


async def get_news_volume(
    db: AsyncSession, symbol: str, *, days: int = 90
) -> list[tuple]:
    from datetime import UTC, datetime, timedelta

    since = datetime.now(UTC) - timedelta(days=days)
    result = await db.execute(
        select(
            func.date(NewsArticle.published_at).label("day"),
            func.count(NewsArticle.id).label("cnt"),
        )
        .join(NewsArticleTicker, NewsArticleTicker.article_id == NewsArticle.id)
        .where(NewsArticleTicker.symbol == symbol, NewsArticle.published_at >= since)
        .group_by(func.date(NewsArticle.published_at))
        .order_by(func.date(NewsArticle.published_at))
    )
    return [(row.day, row.cnt) for row in result.all()]


async def get_news_keywords(db: AsyncSession, symbol: str, *, limit: int = 30) -> list[dict]:
    from collections import Counter
    import re

    since_rows = await db.execute(
        select(NewsArticle.headline, NewsArticle.excerpt)
        .join(NewsArticleTicker, NewsArticleTicker.article_id == NewsArticle.id)
        .where(NewsArticleTicker.symbol == symbol)
        .order_by(desc(NewsArticle.published_at))
        .limit(200)
    )
    texts = []
    for headline, excerpt in since_rows.all():
        texts.append(headline or "")
        if excerpt:
            texts.append(excerpt)
    words: Counter[str] = Counter()
    stop = {"the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of", "is", "psx"}
    for text in texts:
        for w in re.findall(r"[A-Za-z]{4,}", text.lower()):
            if w not in stop:
                words[w] += 1
    return [{"word": w, "weight": c} for w, c in words.most_common(limit)]
