"""Governance routes."""

from fastapi import APIRouter, Depends, HTTPException
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db, get_redis
from backend.routes.tickers import validate_symbol
from backend.schemas.governance import CreditRatingsResponse, GovernanceResponse
from backend.services.cache import cache_get_json, cache_set_json
from backend.services.governance import get_credit_ratings, get_governance

router = APIRouter(tags=["governance"])


@router.get("/ticker/{symbol}/governance", response_model=GovernanceResponse)
async def ticker_governance(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> GovernanceResponse:
    sym = await validate_symbol(symbol, db, redis)
    cache_key = f"ticker:{sym}:governance"
    cached = await cache_get_json(redis, cache_key)
    if cached:
        return GovernanceResponse.model_validate(cached)
    result = await get_governance(db, sym)
    await cache_set_json(redis, cache_key, result.model_dump(), 3600)
    return result


@router.get("/ticker/{symbol}/credit-ratings", response_model=CreditRatingsResponse)
async def ticker_credit_ratings(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> CreditRatingsResponse:
    sym = await validate_symbol(symbol, db, redis)
    cache_key = f"ticker:{sym}:credit-ratings"
    cached = await cache_get_json(redis, cache_key)
    if cached:
        return CreditRatingsResponse.model_validate(cached)
    result = await get_credit_ratings(db, sym)
    await cache_set_json(redis, cache_key, result.model_dump(), 3600)
    return result
