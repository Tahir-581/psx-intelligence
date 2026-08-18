"""Webhook subscription routes (Enterprise / Pro+ when enabled)."""

import hashlib
import hmac
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import require_pro_user
from backend.config import settings
from backend.database import get_db
from backend.models.notification_prefs import WebhookSubscription
from backend.models.user import User

router = APIRouter(tags=["webhooks"])


class WebhookCreate(BaseModel):
    url: str
    event_types: list[str]


class WebhookItem(BaseModel):
    id: int
    url: str
    event_types: list[str]
    is_active: bool


@router.post("/webhooks", response_model=WebhookItem)
async def create_webhook(
    body: WebhookCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_pro_user),
) -> WebhookItem:
    if not settings.webhooks_enabled:
        raise HTTPException(status_code=503, detail="Webhooks not enabled on this deployment")
    import secrets

    secret = secrets.token_hex(32)
    row = WebhookSubscription(
        user_id=user.id,
        url=body.url,
        secret=secret,
        event_types=body.event_types,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return WebhookItem(id=row.id, url=row.url, event_types=row.event_types, is_active=row.is_active)


@router.get("/webhooks", response_model=list[WebhookItem])
async def list_webhooks(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_pro_user),
) -> list[WebhookItem]:
    rows = (
        await db.execute(
            select(WebhookSubscription).where(WebhookSubscription.user_id == user.id)
        )
    ).scalars().all()
    return [
        WebhookItem(id=r.id, url=r.url, event_types=r.event_types, is_active=r.is_active)
        for r in rows
    ]


async def dispatch_webhooks(db: AsyncSession, event_type: str, payload: dict) -> int:
    if not settings.webhooks_enabled:
        return 0
    import httpx

    rows = (
        await db.execute(
            select(WebhookSubscription).where(WebhookSubscription.is_active.is_(True))
        )
    ).scalars().all()
    sent = 0
    body = json.dumps({"event": event_type, "data": payload}).encode()
    for row in rows:
        if event_type not in row.event_types:
            continue
        sig = hmac.new(row.secret.encode(), body, hashlib.sha256).hexdigest()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    row.url,
                    content=body,
                    headers={"X-PSX-Signature": sig, "Content-Type": "application/json"},
                )
                if resp.status_code < 400:
                    sent += 1
        except Exception:
            continue
    return sent
