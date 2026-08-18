from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user_optional
from backend.database import get_db, get_redis
from backend.models.user import User
from backend.routes.tickers import validate_symbol
from backend.schemas.compare import CompareResponse, PeersResponse
from backend.services.compare import get_compare, get_peers

router = APIRouter(tags=["compare"])


@router.get("/compare", response_model=CompareResponse)
async def compare_tickers(
    symbols: str = Query(..., description="Comma-separated symbols, e.g. ENGRO,LUCK"),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    user: User | None = Depends(get_current_user_optional),
) -> CompareResponse:
    sym_list = [s.strip() for s in symbols.split(",") if s.strip()]
    return await get_compare(db, redis, sym_list, user)


@router.get("/ticker/{symbol}/peers", response_model=PeersResponse)
async def ticker_peers(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> PeersResponse:
    sym = await validate_symbol(symbol, db, redis)
    return await get_peers(db, redis, sym)
