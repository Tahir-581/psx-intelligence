"""Notification preferences and push subscription routes."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import require_user
from backend.database import get_db
from backend.models.notification_prefs import PushSubscription, UserNotificationPrefs
from backend.models.user import User

router = APIRouter(tags=["notification-preferences"])


class NotificationPrefsResponse(BaseModel):
    email_enabled: bool
    push_enabled: bool
    whatsapp_enabled: bool
    digest_enabled: bool
    whatsapp_number: str | None = None


class NotificationPrefsUpdate(BaseModel):
    email_enabled: bool | None = None
    push_enabled: bool | None = None
    whatsapp_enabled: bool | None = None
    digest_enabled: bool | None = None
    whatsapp_number: str | None = None


class PushSubscribeRequest(BaseModel):
    endpoint: str
    p256dh: str
    auth: str


@router.get("/notifications/preferences", response_model=NotificationPrefsResponse)
async def get_prefs(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
) -> NotificationPrefsResponse:
    row = await db.get(UserNotificationPrefs, user.id)
    if not row:
        return NotificationPrefsResponse(
            email_enabled=True, push_enabled=False, whatsapp_enabled=False, digest_enabled=True
        )
    return NotificationPrefsResponse(
        email_enabled=row.email_enabled,
        push_enabled=row.push_enabled,
        whatsapp_enabled=row.whatsapp_enabled,
        digest_enabled=row.digest_enabled,
        whatsapp_number=row.whatsapp_number,
    )


@router.patch("/notifications/preferences", response_model=NotificationPrefsResponse)
async def update_prefs(
    body: NotificationPrefsUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
) -> NotificationPrefsResponse:
    row = await db.get(UserNotificationPrefs, user.id)
    if not row:
        row = UserNotificationPrefs(user_id=user.id)
        db.add(row)
    for field in ("email_enabled", "push_enabled", "whatsapp_enabled", "digest_enabled", "whatsapp_number"):
        val = getattr(body, field)
        if val is not None:
            setattr(row, field, val)
    await db.commit()
    await db.refresh(row)
    return NotificationPrefsResponse(
        email_enabled=row.email_enabled,
        push_enabled=row.push_enabled,
        whatsapp_enabled=row.whatsapp_enabled,
        digest_enabled=row.digest_enabled,
        whatsapp_number=row.whatsapp_number,
    )


@router.post("/notifications/push-subscribe", status_code=204)
async def push_subscribe(
    body: PushSubscribeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
) -> None:
    existing = await db.scalar(
        select(PushSubscription).where(
            PushSubscription.user_id == user.id,
            PushSubscription.endpoint == body.endpoint,
        )
    )
    if existing:
        return
    db.add(
        PushSubscription(
            user_id=user.id,
            endpoint=body.endpoint,
            p256dh=body.p256dh,
            auth=body.auth,
        )
    )
    await db.commit()
