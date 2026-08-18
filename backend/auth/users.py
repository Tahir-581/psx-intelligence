"""User sync helpers."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.user import User


async def upsert_user(
    db: AsyncSession,
    user_id: str,
    email: str | None = None,
) -> User:
    stmt = insert(User).values(
        {
            "id": user_id,
            "email": email or f"{user_id}@clerk.local",
            "plan_tier": "free",
        }
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={"email": stmt.excluded.email},
    )
    await db.execute(stmt)
    await db.commit()
    user = await db.scalar(select(User).where(User.id == user_id))
    assert user is not None
    return user


async def get_user(db: AsyncSession, user_id: str) -> User | None:
    return await db.scalar(select(User).where(User.id == user_id))
