from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user_optional, require_pro_user
from backend.auth.entitlements import financial_period_limit, is_pro
from backend.database import get_db, get_redis
from backend.models.user import User
from backend.routes.tickers import validate_symbol
from backend.schemas.fundamentals import (
    AnnouncementListResponse,
    FinancialsResponse,
    InsiderTradesResponse,
    OwnershipResponse,
    RatiosResponse,
)
from backend.services.cache import cache_get_json, cache_set_json
from backend.services.fundamentals import (
    get_announcements,
    get_financials,
    get_insider_trades,
    get_ownership,
    get_ratios,
)

router = APIRouter(tags=["fundamentals"])


@router.get("/ticker/{symbol}/announcements", response_model=AnnouncementListResponse)
async def ticker_announcements(
    symbol: str,
    category: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> AnnouncementListResponse:
    sym = await validate_symbol(symbol, db, redis)
    cache_key = f"ticker:{sym}:announcements:{category}:{page}:{page_size}"
    cached = await cache_get_json(redis, cache_key)
    if cached:
        return AnnouncementListResponse.model_validate(cached)
    result = await get_announcements(db, sym, category=category, page=page, page_size=page_size)
    await cache_set_json(redis, cache_key, result.model_dump(), 300)
    return result


@router.get("/ticker/{symbol}/financials", response_model=FinancialsResponse)
async def ticker_financials(
    symbol: str,
    period_type: str = Query("quarterly", pattern="^(quarterly|annual)$"),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    user: User | None = Depends(get_current_user_optional),
) -> FinancialsResponse:
    sym = await validate_symbol(symbol, db, redis)
    pro = is_pro(user)
    cache_key = f"ticker:{sym}:financials:{period_type}:{pro}"
    cached = await cache_get_json(redis, cache_key)
    if cached:
        return FinancialsResponse.model_validate(cached)
    max_periods = financial_period_limit(user) if period_type == "quarterly" else None
    result = await get_financials(db, sym, period_type=period_type, max_periods=max_periods)
    await cache_set_json(redis, cache_key, result.model_dump(), 3600)
    return result


@router.get("/ticker/{symbol}/ratios", response_model=RatiosResponse)
async def ticker_ratios(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> RatiosResponse:
    sym = await validate_symbol(symbol, db, redis)
    cache_key = f"ticker:{sym}:ratios"
    cached = await cache_get_json(redis, cache_key)
    if cached:
        return RatiosResponse.model_validate(cached)
    result = await get_ratios(db, sym)
    await cache_set_json(redis, cache_key, result.model_dump(), 3600)
    return result


@router.get("/ticker/{symbol}/insider-trades", response_model=InsiderTradesResponse)
async def ticker_insider_trades(
    symbol: str,
    days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> InsiderTradesResponse:
    sym = await validate_symbol(symbol, db, redis)
    cache_key = f"ticker:{sym}:insider:{days}"
    cached = await cache_get_json(redis, cache_key)
    if cached:
        return InsiderTradesResponse.model_validate(cached)
    result = await get_insider_trades(db, sym, days=days)
    await cache_set_json(redis, cache_key, result.model_dump(), 300)
    return result


@router.get("/ticker/{symbol}/ownership", response_model=OwnershipResponse)
async def ticker_ownership(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> OwnershipResponse:
    sym = await validate_symbol(symbol, db, redis)
    cache_key = f"ticker:{sym}:ownership"
    cached = await cache_get_json(redis, cache_key)
    if cached:
        return OwnershipResponse.model_validate(cached)
    result = await get_ownership(db, sym)
    await cache_set_json(redis, cache_key, result.model_dump(), 3600)
    return result


@router.get("/ticker/{symbol}/financials/export")
async def ticker_financials_export(
    symbol: str,
    period_type: str = Query("quarterly", pattern="^(quarterly|annual)$"),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    user: User = Depends(require_pro_user),
):
    import csv
    import io

    sym = await validate_symbol(symbol, db, redis)
    result = await get_financials(db, sym, period_type=period_type)
    buf = io.StringIO()
    writer = csv.writer(buf)
    headers = ["line_code"] + [p.period_end.isoformat() for p in result.periods]
    writer.writerow(headers)
    for row in result.rows:
        writer.writerow([row.line_code] + [row.values.get(h, "") for h in headers[1:]])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{sym}_financials.csv"'},
    )
