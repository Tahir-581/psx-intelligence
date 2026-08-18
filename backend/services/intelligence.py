"""Intelligence layer services — sentiment, social, AI summaries."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.ai_summary import AiSummary
from backend.models.sentiment_score import SentimentScore
from backend.models.social_post import SocialPost
from backend.models.social_post_ticker import SocialPostTicker
from backend.schemas.intelligence import (
    AiSummaryResponse,
    SentimentDataPoint,
    SentimentSeriesResponse,
    SocialFeedResponse,
    SocialPostItem,
)
from nlp.sentiment import get_cached_article_sentiment


async def get_ticker_sentiment(
    db: AsyncSession,
    symbol: str,
    *,
    days: int = 90,
) -> SentimentSeriesResponse:
    since = datetime.now(UTC) - timedelta(days=days)
    rows = (
        await db.execute(
            select(SentimentScore)
            .where(SentimentScore.symbol == symbol, SentimentScore.time >= since)
            .order_by(SentimentScore.time)
        )
    ).scalars().all()

    aggregate: list[SentimentDataPoint] = []
    by_source: dict[str, list[SentimentDataPoint]] = {}

    for row in rows:
        point = SentimentDataPoint(
            time=row.time,
            source=row.source,
            score=float(row.score),
            positive_pct=float(row.positive_pct) if row.positive_pct else None,
            negative_pct=float(row.negative_pct) if row.negative_pct else None,
            neutral_pct=float(row.neutral_pct) if row.neutral_pct else None,
            post_count=row.post_count,
        )
        if row.source == "aggregate":
            aggregate.append(point)
        else:
            by_source.setdefault(row.source, []).append(point)

    current_score = aggregate[-1].score if aggregate else None
    momentum = None
    if len(aggregate) >= 4:
        momentum = round(aggregate[-1].score - aggregate[-4].score, 4)

    price_divergence = None
    divergence_note = None
    if len(aggregate) >= 5 and momentum is not None:
        from backend.services.market import get_prices

        prices = await get_prices(db, symbol)
        if prices.bars and len(prices.bars) >= 5:
            price_chg = prices.bars[-1].close - prices.bars[-5].close
            sent_chg = aggregate[-1].score - aggregate[-5].score
            if price_chg > 0 and sent_chg < -0.1:
                price_divergence = True
                divergence_note = "Price rising while sentiment falling — potential divergence"
            elif price_chg < 0 and sent_chg > 0.1:
                price_divergence = True
                divergence_note = "Price falling while sentiment improving — potential reversal signal"

    return SentimentSeriesResponse(
        symbol=symbol,
        days=days,
        aggregate=aggregate,
        by_source=by_source,
        momentum_3d=momentum,
        current_score=current_score,
        price_divergence=price_divergence,
        divergence_note=divergence_note,
    )


async def get_sentiment_price_overlay(
    db: AsyncSession, symbol: str, *, days: int = 90
) -> SentimentPriceOverlayResponse:
    from backend.schemas.intelligence import SentimentPriceOverlayPoint, SentimentPriceOverlayResponse
    from backend.services.market import get_prices

    sentiment = await get_ticker_sentiment(db, symbol, days=days)
    prices = await get_prices(db, symbol)
    if not prices.bars or not sentiment.aggregate:
        return SentimentPriceOverlayResponse(symbol=symbol, days=days, points=[])
    base_price = prices.bars[0].close
    price_by_day = {b.time.date(): b.close for b in prices.bars}
    points = []
    for pt in sentiment.aggregate:
        day = pt.time.date()
        close = price_by_day.get(day)
        if close is None:
            continue
        points.append(
            SentimentPriceOverlayPoint(
                time=pt.time,
                sentiment=pt.score,
                price_normalized=(close / base_price) * 100 if base_price else 100,
            )
        )
    return SentimentPriceOverlayResponse(symbol=symbol, days=days, points=points)


async def get_weekly_summary(db: AsyncSession, symbol: str) -> AiSummaryResponse | None:
    row = await db.scalar(
        select(AiSummary)
        .where(AiSummary.symbol == symbol, AiSummary.summary_type == "company_weekly")
        .order_by(desc(AiSummary.generated_at))
        .limit(1)
    )
    if not row:
        return None
    return AiSummaryResponse(
        symbol=row.symbol,
        summary_type=row.summary_type,
        content=row.content,
        generated_at=row.generated_at,
        model=row.model,
    )


async def get_ticker_social(
    db: AsyncSession,
    symbol: str,
    *,
    days: int = 30,
    page: int = 1,
    page_size: int = 20,
) -> SocialFeedResponse:
    since = datetime.now(UTC) - timedelta(days=days)
    query = (
        select(SocialPost, SocialPostTicker.link_confidence)
        .join(SocialPostTicker, SocialPostTicker.post_id == SocialPost.id)
        .where(SocialPostTicker.symbol == symbol, SocialPost.posted_at >= since)
    )
    count_q = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_q) or 0
    result = await db.execute(
        query.order_by(desc(SocialPost.posted_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [
        SocialPostItem(
            id=post.id,
            source=post.source,
            author_handle=post.author_handle,
            posted_at=post.posted_at,
            text=post.text,
            url=post.url,
            engagement_json=post.engagement_json,
            link_confidence=float(conf) if conf else None,
        )
        for post, conf in result.all()
    ]
    return SocialFeedResponse(symbol=symbol, items=items, total=total)


async def get_article_ai_summary(db: AsyncSession, article_id: int) -> str | None:
    row = await db.scalar(
        select(AiSummary.content).where(
            AiSummary.summary_type == "news_article",
            AiSummary.reference_id == article_id,
        )
    )
    return row


def get_article_sentiment_badge(article_id: int) -> str | None:
    cached = get_cached_article_sentiment(article_id)
    if cached:
        return cached[1]
    return None
