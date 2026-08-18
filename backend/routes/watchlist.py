from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import require_user
from backend.database import get_db, get_redis
from backend.models.user import User
from backend.routes.tickers import validate_symbol
from backend.schemas.intelligence import WatchlistResponse
from backend.services.watchlist import add_to_watchlist, get_watchlist, remove_from_watchlist

router = APIRouter(tags=["watchlist"])


@router.get("/watchlist", response_model=WatchlistResponse)
async def list_watchlist(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    user: User = Depends(require_user),
) -> WatchlistResponse:
    return await get_watchlist(db, redis, user)


@router.post("/watchlist/{symbol}", response_model=WatchlistResponse)
async def add_watchlist_symbol(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    user: User = Depends(require_user),
) -> WatchlistResponse:
    sym = await validate_symbol(symbol, db, redis)
    return await add_to_watchlist(db, redis, user, sym)


@router.delete("/watchlist/{symbol}", response_model=WatchlistResponse)
async def remove_watchlist_symbol(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    user: User = Depends(require_user),
) -> WatchlistResponse:
    return await remove_from_watchlist(db, redis, user, symbol)
