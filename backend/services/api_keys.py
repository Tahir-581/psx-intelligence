"""Pro API key management."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.models.api_key import ApiKey
from backend.models.user import User
from backend.schemas.api_keys import ApiKeyCreateResponse, ApiKeyItem, ApiKeyListResponse


def _hash_key(raw_key: str) -> str:
    salt = settings.api_key_hash_salt or "psx-default-salt"
    return hashlib.sha256(f"{salt}:{raw_key}".encode()).hexdigest()


async def create_api_key(
    db: AsyncSession, user: User, label: str
) -> ApiKeyCreateResponse:
    raw = f"psx_live_{secrets.token_urlsafe(32)}"
    prefix = raw[:12]
    record = ApiKey(
        user_id=user.id,
        key_prefix=prefix,
        key_hash=_hash_key(raw),
        label=label,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return ApiKeyCreateResponse(
        id=record.id,
        key=raw,
        key_prefix=prefix,
        label=label,
        created_at=record.created_at,
    )


async def list_api_keys(db: AsyncSession, user: User) -> ApiKeyListResponse:
    rows = (
        await db.execute(
            select(ApiKey)
            .where(ApiKey.user_id == user.id, ApiKey.revoked_at.is_(None))
            .order_by(ApiKey.created_at.desc())
        )
    ).scalars().all()
    return ApiKeyListResponse(
        items=[
            ApiKeyItem(
                id=k.id,
                key_prefix=k.key_prefix,
                label=k.label,
                last_used_at=k.last_used_at,
                created_at=k.created_at,
            )
            for k in rows
        ]
    )


async def revoke_api_key(db: AsyncSession, user: User, key_id: int) -> None:
    key = await db.scalar(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user.id)
    )
    if not key:
        raise HTTPException(status_code=404, detail="API key not found.")
    key.revoked_at = datetime.now(UTC)
    await db.commit()


async def authenticate_api_key(db: AsyncSession, raw_key: str) -> User | None:
    if not raw_key.startswith("psx_live_"):
        return None
    prefix = raw_key[:12]
    record = await db.scalar(
        select(ApiKey).where(
            ApiKey.key_prefix == prefix,
            ApiKey.revoked_at.is_(None),
        )
    )
    if not record or record.key_hash != _hash_key(raw_key):
        return None
    record.last_used_at = datetime.now(UTC)
    user = await db.get(User, record.user_id)
    if not user:
        return None
    await db.commit()
    return user
