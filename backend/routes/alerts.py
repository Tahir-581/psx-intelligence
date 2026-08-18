from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import require_pro_user, require_user
from backend.database import get_db, get_redis
from backend.models.user import User
from backend.schemas.alerts import (
    AlertCreate,
    AlertEventListResponse,
    AlertItem,
    AlertListResponse,
    AlertUpdate,
)
from backend.services.alerts import (
    create_alert,
    delete_alert,
    list_alert_events,
    list_alerts,
    update_alert,
)

router = APIRouter(tags=["alerts"])


@router.get("/alerts", response_model=AlertListResponse)
async def get_alerts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_pro_user),
) -> AlertListResponse:
    return await list_alerts(db, user)


@router.post("/alerts", response_model=AlertItem)
async def post_alert(
    body: AlertCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_pro_user),
) -> AlertItem:
    return await create_alert(db, user, body)


@router.patch("/alerts/{alert_id}", response_model=AlertItem)
async def patch_alert(
    alert_id: int,
    body: AlertUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_pro_user),
) -> AlertItem:
    return await update_alert(db, user, alert_id, body)


@router.delete("/alerts/{alert_id}", status_code=204)
async def remove_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_pro_user),
) -> None:
    await delete_alert(db, user, alert_id)


@router.get("/alerts/events", response_model=AlertEventListResponse)
async def get_alert_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_pro_user),
) -> AlertEventListResponse:
    return await list_alert_events(db, user, page=page, page_size=page_size)
