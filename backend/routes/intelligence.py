from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import require_pro_user, require_user
from backend.database import get_db, get_redis
from backend.models.user import User
from backend.routes.tickers import validate_symbol
from backend.schemas.intelligence import (
    AiSummaryResponse,
    SentimentPriceOverlayResponse,
    SentimentSeriesResponse,
    SocialFeedResponse,
)
from backend.services.cache import cache_get_json, cache_set_json
from backend.services.intelligence import (
    get_sentiment_price_overlay,
    get_ticker_sentiment,
    get_ticker_social,
    get_weekly_summary,
)

router = APIRouter(tags=["intelligence"])


@router.get("/ticker/{symbol}/sentiment", response_model=SentimentSeriesResponse)
async def ticker_sentiment(
    symbol: str,
    days: int = Query(90, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    user: User = Depends(require_pro_user),
) -> SentimentSeriesResponse:
    sym = await validate_symbol(symbol, db, redis)
    cache_key = f"ticker:{sym}:sentiment:{days}"
    cached = await cache_get_json(redis, cache_key)
    if cached:
        return SentimentSeriesResponse.model_validate(cached)
    result = await get_ticker_sentiment(db, sym, days=days)
    await cache_set_json(redis, cache_key, result.model_dump(), 3600)
    return result


@router.get("/ticker/{symbol}/summary", response_model=AiSummaryResponse)
async def ticker_summary(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    user: User = Depends(require_pro_user),
) -> AiSummaryResponse:
    sym = await validate_symbol(symbol, db, redis)
    cache_key = f"ticker:{sym}:summary"
    cached = await cache_get_json(redis, cache_key)
    if cached:
        return AiSummaryResponse.model_validate(cached)
    result = await get_weekly_summary(db, sym)
    if not result:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="No summary available")
    await cache_set_json(redis, cache_key, result.model_dump(), 604800)
    return result


@router.get("/ticker/{symbol}/social", response_model=SocialFeedResponse)
async def ticker_social(
    symbol: str,
    days: int = Query(30, ge=1, le=90),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    user: User = Depends(require_pro_user),
) -> SocialFeedResponse:
    sym = await validate_symbol(symbol, db, redis)
    result = await get_ticker_social(db, sym, days=days, page=page, page_size=page_size)
    return result


@router.get("/ticker/{symbol}/sentiment/price-overlay", response_model=SentimentPriceOverlayResponse)
async def ticker_sentiment_price_overlay(
    symbol: str,
    days: int = Query(90, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    user: User = Depends(require_pro_user),
) -> SentimentPriceOverlayResponse:
    sym = await validate_symbol(symbol, db, redis)
    return await get_sentiment_price_overlay(db, sym, days=days)


@router.post("/ticker/{symbol}/summary/refresh", response_model=AiSummaryResponse)
async def refresh_summary(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    user: User = Depends(require_pro_user),
) -> AiSummaryResponse:
    from datetime import UTC, datetime
    from fastapi import HTTPException

    sym = await validate_symbol(symbol, db, redis)
    rate_key = f"summary_refresh:{user.id}:{sym}"
    if await redis.get(rate_key):
        raise HTTPException(status_code=429, detail="Refresh limited to once per 24 hours per ticker")
    from nlp.ai_summaries import generate_single_company_summary

    ok = generate_single_company_summary(sym)
    if not ok:
        raise HTTPException(status_code=503, detail="Summary generation unavailable")
    await redis.setex(rate_key, 86400, datetime.now(UTC).isoformat())
    await redis.delete(f"ticker:{sym}:summary")
    result = await get_weekly_summary(db, sym)
    if not result:
        raise HTTPException(status_code=404, detail="Summary not stored")
    return result
