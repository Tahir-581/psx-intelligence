from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db, get_redis
from backend.models.ticker import Ticker
from backend.schemas.market import (
    ChartMarkersResponse,
    DataHealthResponse,
    MarketSummaryResponse,
    PriceSeriesResponse,
    SnapshotResponse,
    TickerListResponse,
)
from backend.services.cache import cache_get_json, cache_set_json
from backend.services.chart_markers import get_chart_markers
from backend.services.market import (
    get_data_health,
    get_market_summary,
    get_prices,
    get_snapshot,
    get_tickers,
)

router = APIRouter(tags=["tickers"])


async def validate_symbol(
    symbol: str, db: AsyncSession, redis: Redis
) -> str:
    sym = symbol.upper()
    in_whitelist = await redis.sismember("symbols:whitelist", sym)
    if in_whitelist:
        return sym
    exists = await db.scalar(select(Ticker.symbol).where(Ticker.symbol == sym))
    if not exists:
        raise HTTPException(status_code=404, detail=f"Unknown symbol: {sym}")
    return sym


@router.get("/tickers", response_model=TickerListResponse)
async def list_tickers(
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> TickerListResponse:
    cache_key = f"tickers:list:{search}:{page}:{page_size}"
    cached = await cache_get_json(redis, cache_key)
    if cached:
        return TickerListResponse.model_validate(cached)
    result = await get_tickers(db, redis, search=search, page=page, page_size=page_size)
    await cache_set_json(redis, cache_key, result.model_dump(), 3600)
    return result


@router.get("/ticker/{symbol}/snapshot", response_model=SnapshotResponse)
async def ticker_snapshot(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> SnapshotResponse:
    sym = await validate_symbol(symbol, db, redis)
    cache_key = f"ticker:{sym}:snapshot:api"
    cached = await cache_get_json(redis, cache_key)
    if cached:
        return SnapshotResponse.model_validate(cached)
    snapshot = await get_snapshot(db, redis, sym)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Ticker not found")
    await cache_set_json(redis, cache_key, snapshot.model_dump(), 60)
    return snapshot


@router.get("/ticker/{symbol}/prices", response_model=PriceSeriesResponse)
async def ticker_prices(
    symbol: str,
    from_dt: datetime | None = Query(None, alias="from"),
    to_dt: datetime | None = Query(None, alias="to"),
    overlay: str | None = Query(None),
    adjusted: bool = Query(False),
    overlays: str | None = Query(None, description="Comma-separated: SMA20,SMA50,SMA200,EMA12,EMA26,BB20,VOLMA20"),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> PriceSeriesResponse:
    sym = await validate_symbol(symbol, db, redis)
    cache_key = f"ticker:{sym}:prices:{from_dt}:{to_dt}:{overlay}:{adjusted}:{overlays}"
    cached = await cache_get_json(redis, cache_key)
    if cached:
        return PriceSeriesResponse.model_validate(cached)
    series = await get_prices(
        db, sym, from_dt=from_dt, to_dt=to_dt, overlay=overlay,
        adjusted=adjusted, overlays=overlays,
    )
    await cache_set_json(redis, cache_key, series.model_dump(), 300)
    return series


@router.get("/ticker/{symbol}/chart-markers", response_model=ChartMarkersResponse)
async def ticker_chart_markers(
    symbol: str,
    from_dt: datetime | None = Query(None, alias="from"),
    to_dt: datetime | None = Query(None, alias="to"),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> ChartMarkersResponse:
    sym = await validate_symbol(symbol, db, redis)
    return await get_chart_markers(db, sym, from_dt=from_dt, to_dt=to_dt)


@router.get("/market/summary", response_model=MarketSummaryResponse)
async def market_summary(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> MarketSummaryResponse:
    cache_key = "market:summary"
    cached = await cache_get_json(redis, cache_key)
    if cached:
        return MarketSummaryResponse.model_validate(cached)
    summary = await get_market_summary(db, redis)
    await cache_set_json(redis, cache_key, summary.model_dump(), 60)
    return summary


@router.get("/health/data", response_model=DataHealthResponse)
async def data_health(db: AsyncSession = Depends(get_db)) -> DataHealthResponse:
    return await get_data_health(db)
