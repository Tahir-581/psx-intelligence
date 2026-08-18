from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import require_user
from backend.database import get_db
from backend.models.user import User
from backend.schemas.notifications import NotificationListResponse
from backend.services.notifications import (
    list_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)

router = APIRouter(tags=["notifications"])


@router.get("/notifications", response_model=NotificationListResponse)
async def get_notifications(
    unread_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
) -> NotificationListResponse:
    return await list_notifications(
        db, user, unread_only=unread_only, page=page, page_size=page_size
    )


@router.patch("/notifications/{notification_id}/read", status_code=204)
async def read_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
) -> None:
    await mark_notification_read(db, user, notification_id)


@router.post("/notifications/read-all", status_code=204)
async def read_all_notifications(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
) -> None:
    await mark_all_notifications_read(db, user)
