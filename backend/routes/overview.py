from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db, get_redis
from backend.routes.tickers import validate_symbol
from backend.schemas.overview import OverviewResponse
from backend.services.cache import cache_get_json, cache_set_json
from backend.services.overview import get_overview

router = APIRouter(tags=["overview"])


@router.get("/ticker/{symbol}/overview", response_model=OverviewResponse)
async def ticker_overview(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> OverviewResponse:
    sym = await validate_symbol(symbol, db, redis)
    cache_key = f"ticker:{sym}:overview"
    cached = await cache_get_json(redis, cache_key)
    if cached:
        return OverviewResponse.model_validate(cached)
    result = await get_overview(db, sym)
    await cache_set_json(redis, cache_key, result.model_dump(), 120)
    return result
