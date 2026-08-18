import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import require_pro_user
from backend.database import get_db, get_redis
from backend.models.user import User
from backend.schemas.portfolio import (
    HoldingCreate,
    HoldingUpdate,
    PortfolioResponse,
    TransactionListResponse,
)
from backend.services.portfolio import (
    add_holding,
    delete_holding,
    get_portfolio,
    list_transactions,
    portfolio_to_csv,
    update_holding,
)

router = APIRouter(tags=["portfolio"])


@router.get("/portfolio", response_model=PortfolioResponse)
async def fetch_portfolio(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    user: User = Depends(require_pro_user),
) -> PortfolioResponse:
    return await get_portfolio(db, redis, user)


@router.post("/portfolio/holdings", response_model=PortfolioResponse)
async def create_holding(
    body: HoldingCreate,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    user: User = Depends(require_pro_user),
) -> PortfolioResponse:
    return await add_holding(db, redis, user, body)


@router.patch("/portfolio/holdings/{holding_id}", response_model=PortfolioResponse)
async def patch_holding(
    holding_id: int,
    body: HoldingUpdate,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    user: User = Depends(require_pro_user),
) -> PortfolioResponse:
    return await update_holding(db, redis, user, holding_id, body)


@router.delete("/portfolio/holdings/{holding_id}", response_model=PortfolioResponse)
async def remove_holding(
    holding_id: int,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    user: User = Depends(require_pro_user),
) -> PortfolioResponse:
    return await delete_holding(db, redis, user, holding_id)


@router.get("/portfolio/transactions", response_model=TransactionListResponse)
async def fetch_transactions(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_pro_user),
) -> TransactionListResponse:
    return await list_transactions(db, user)


@router.get("/portfolio/export")
async def export_portfolio(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    user: User = Depends(require_pro_user),
) -> StreamingResponse:
    data = await get_portfolio(db, redis, user)
    csv_text = portfolio_to_csv(data)
    return StreamingResponse(
        io.StringIO(csv_text),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=portfolio.csv"},
    )
