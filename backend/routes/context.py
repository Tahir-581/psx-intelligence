from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user_optional
from backend.auth.entitlements import is_pro, news_cutoff
from backend.database import get_db, get_redis
from backend.models.user import User
from backend.routes.tickers import validate_symbol
from backend.schemas.context import (
    BetaResponse,
    CorpActionAnalyticsResponse,
    CorporateActionListResponse,
    CorporateCalendarResponse,
    MacroSeriesResponse,
    MaterialEventListResponse,
    NewsKeywordsResponse,
    NewsListResponse,
    NewsVolumePoint,
    NewsVolumeResponse,
    SectorDetailResponse,
    SectorStatsResponse,
)
from backend.services.cache import cache_get_json, cache_set_json
from backend.services.corporate_analytics import get_corporate_action_analytics
from backend.services.corporate_actions import (
    get_corporate_actions,
    get_corporate_calendar,
)
from backend.services.macro import get_macro_series
from backend.services.material_events import get_material_events
from backend.services.news import get_news_keywords, get_news_volume, get_ticker_news
from backend.services.risk import get_beta
from backend.services.sector import get_sector_detail, get_sector_stats

router = APIRouter(tags=["context"])


@router.get("/ticker/{symbol}/news", response_model=NewsListResponse)
async def ticker_news(
    symbol: str,
    source: str | None = None,
    topic: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    user: User | None = Depends(get_current_user_optional),
) -> NewsListResponse:
    sym = await validate_symbol(symbol, db, redis)
    pro = is_pro(user)
    cutoff = news_cutoff(user)
    cache_key = f"ticker:{sym}:news:{source}:{topic}:{page}:{page_size}:{pro}"
    cached = await cache_get_json(redis, cache_key)
    if cached:
        return NewsListResponse.model_validate(cached)
    result = await get_ticker_news(
        db,
        sym,
        source=source,
        topic=topic,
        page=page,
        page_size=page_size,
        published_after=cutoff,
        include_pro_fields=pro,
    )
    await cache_set_json(redis, cache_key, result.model_dump(), 300)
    return result


@router.get("/ticker/{symbol}/corporate-actions", response_model=CorporateActionListResponse)
async def ticker_corporate_actions(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> CorporateActionListResponse:
    sym = await validate_symbol(symbol, db, redis)
    cache_key = f"ticker:{sym}:corporate-actions"
    cached = await cache_get_json(redis, cache_key)
    if cached:
        return CorporateActionListResponse.model_validate(cached)
    result = await get_corporate_actions(db, sym)
    await cache_set_json(redis, cache_key, result.model_dump(), 3600)
    return result


@router.get("/ticker/{symbol}/events", response_model=MaterialEventListResponse)
async def ticker_events(
    symbol: str,
    min_significance: int = Query(1, ge=1, le=5),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> MaterialEventListResponse:
    sym = await validate_symbol(symbol, db, redis)
    cache_key = f"ticker:{sym}:events:{min_significance}"
    cached = await cache_get_json(redis, cache_key)
    if cached:
        return MaterialEventListResponse.model_validate(cached)
    result = await get_material_events(db, sym, min_significance=min_significance)
    await cache_set_json(redis, cache_key, result.model_dump(), 300)
    return result


@router.get("/ticker/{symbol}/beta", response_model=BetaResponse)
async def ticker_beta(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> BetaResponse:
    sym = await validate_symbol(symbol, db, redis)
    return await get_beta(db, redis, sym)


@router.get("/macro/{series_code}", response_model=MacroSeriesResponse)
async def macro_series(
    series_code: str,
    from_dt: datetime | None = Query(None, alias="from"),
    to_dt: datetime | None = Query(None, alias="to"),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> MacroSeriesResponse:
    cache_key = f"macro:{series_code}:{from_dt}:{to_dt}"
    cached = await cache_get_json(redis, cache_key)
    if cached:
        return MacroSeriesResponse.model_validate(cached)
    result = await get_macro_series(db, series_code, from_dt=from_dt, to_dt=to_dt)
    await cache_set_json(redis, cache_key, result.model_dump(), 3600)
    return result


@router.get("/market/sectors", response_model=SectorStatsResponse)
async def market_sectors(
    range: str = Query("1d", pattern="^(1d|1w|1m|ytd)$"),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> SectorStatsResponse:
    cache_key = f"market:sectors:{range}"
    cached = await cache_get_json(redis, cache_key)
    if cached:
        return SectorStatsResponse.model_validate(cached)
    result = await get_sector_stats(db, range_key=range)
    await cache_set_json(redis, cache_key, result.model_dump(), 300)
    return result


@router.get("/market/sectors/{sector}/detail", response_model=SectorDetailResponse)
async def market_sector_detail(
    sector: str,
    range: str = Query("1d", pattern="^(1d|1w|1m|ytd)$"),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> SectorDetailResponse:
    cache_key = f"market:sector-detail:{sector}:{range}"
    cached = await cache_get_json(redis, cache_key)
    if cached:
        return SectorDetailResponse.model_validate(cached)
    result = await get_sector_detail(db, redis, sector, range_key=range)
    await cache_set_json(redis, cache_key, result.model_dump(), 300)
    return result


@router.get("/market/corporate-calendar", response_model=CorporateCalendarResponse)
async def corporate_calendar(
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> CorporateCalendarResponse:
    cache_key = f"market:corporate-calendar:{from_date}:{to_date}"
    cached = await cache_get_json(redis, cache_key)
    if cached:
        return CorporateCalendarResponse.model_validate(cached)
    result = await get_corporate_calendar(db, from_date=from_date, to_date=to_date)
    await cache_set_json(redis, cache_key, result.model_dump(), 600)
    return result


@router.get("/ticker/{symbol}/corporate-actions/analytics", response_model=CorpActionAnalyticsResponse)
async def ticker_corp_analytics(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> CorpActionAnalyticsResponse:
    sym = await validate_symbol(symbol, db, redis)
    return await get_corporate_action_analytics(db, sym)


@router.get("/ticker/{symbol}/news/volume", response_model=NewsVolumeResponse)
async def ticker_news_volume(
    symbol: str,
    days: int = Query(90, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> NewsVolumeResponse:
    sym = await validate_symbol(symbol, db, redis)
    points = await get_news_volume(db, sym, days=days)
    return NewsVolumeResponse(
        symbol=sym,
        days=days,
        points=[NewsVolumePoint(date=d, count=c) for d, c in points],
    )


@router.get("/ticker/{symbol}/news/keywords", response_model=NewsKeywordsResponse)
async def ticker_news_keywords(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    user: User | None = Depends(get_current_user_optional),
) -> NewsKeywordsResponse:
    from backend.auth.entitlements import is_pro
    from fastapi import HTTPException

    if not is_pro(user):
        raise HTTPException(status_code=403, detail="Pro subscription required")
    sym = await validate_symbol(symbol, db, redis)
    keywords = await get_news_keywords(db, sym)
    return NewsKeywordsResponse(symbol=sym, keywords=keywords)
