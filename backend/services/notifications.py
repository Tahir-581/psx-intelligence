"""In-app notifications inbox."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.notification import Notification
from backend.models.user import User
from backend.schemas.notifications import NotificationItem, NotificationListResponse


async def list_notifications(
    db: AsyncSession,
    user: User,
    *,
    unread_only: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> NotificationListResponse:
    base = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        base = base.where(Notification.read_at.is_(None))
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    unread = await db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user.id, Notification.read_at.is_(None))
    ) or 0
    rows = (
        await db.execute(
            base.order_by(desc(Notification.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    return NotificationListResponse(
        items=[
            NotificationItem(
                id=n.id,
                title=n.title,
                body=n.body,
                link_url=n.link_url,
                read_at=n.read_at,
                created_at=n.created_at,
            )
            for n in rows
        ],
        total=total,
        unread_count=unread,
        page=page,
        page_size=page_size,
    )


async def mark_notification_read(db: AsyncSession, user: User, notification_id: int) -> None:
    notif = await db.scalar(
        select(Notification).where(
            Notification.id == notification_id, Notification.user_id == user.id
        )
    )
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found.")
    notif.read_at = datetime.now(UTC)
    await db.commit()


async def mark_all_notifications_read(db: AsyncSession, user: User) -> None:
    rows = (
        await db.execute(
            select(Notification).where(
                Notification.user_id == user.id, Notification.read_at.is_(None)
            )
        )
    ).scalars().all()
    now = datetime.now(UTC)
    for n in rows:
        n.read_at = now
    await db.commit()
