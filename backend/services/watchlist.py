"""Watchlist service."""

from __future__ import annotations

from fastapi import HTTPException
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.entitlements import watchlist_limit
from backend.models.user import User
from backend.models.watchlist import Watchlist
from backend.models.watchlist_item import WatchlistItem
from backend.schemas.intelligence import WatchlistItemSnapshot, WatchlistResponse
from backend.services.market import get_snapshot


async def _get_or_create_watchlist(db: AsyncSession, user_id: str) -> Watchlist:
    wl = await db.scalar(
        select(Watchlist).where(Watchlist.user_id == user_id, Watchlist.name == "default")
    )
    if wl:
        return wl
    wl = Watchlist(user_id=user_id, name="default")
    db.add(wl)
    await db.flush()
    return wl


async def get_watchlist(db: AsyncSession, redis: Redis, user: User) -> WatchlistResponse:
    wl = await _get_or_create_watchlist(db, user.id)
    items = (
        await db.execute(
            select(WatchlistItem)
            .where(WatchlistItem.watchlist_id == wl.id)
            .order_by(WatchlistItem.added_at)
        )
    ).scalars().all()

    snapshots: list[WatchlistItemSnapshot] = []
    for item in items:
        snap = await get_snapshot(db, redis, item.symbol)
        snapshots.append(
            WatchlistItemSnapshot(
                symbol=item.symbol,
                name=snap.name if snap else None,
                ltp=snap.ltp if snap else None,
                change_pct=snap.change_pct if snap else None,
                added_at=item.added_at,
            )
        )

    return WatchlistResponse(
        items=snapshots,
        limit=watchlist_limit(user),
        count=len(snapshots),
    )


async def add_to_watchlist(
    db: AsyncSession, redis: Redis, user: User, symbol: str
) -> WatchlistResponse:
    wl = await _get_or_create_watchlist(db, user.id)
    sym = symbol.upper()
    existing = await db.scalar(
        select(WatchlistItem).where(
            WatchlistItem.watchlist_id == wl.id, WatchlistItem.symbol == sym
        )
    )
    if existing:
        return await get_watchlist(db, redis, user)

    count = await db.scalar(
        select(func.count()).select_from(WatchlistItem).where(WatchlistItem.watchlist_id == wl.id)
    ) or 0
    limit = watchlist_limit(user)
    if limit is not None and count >= limit:
        raise HTTPException(status_code=403, detail=f"Free plan limited to {limit} watchlist symbols")

    db.add(WatchlistItem(watchlist_id=wl.id, symbol=sym))
    await db.commit()
    return await get_watchlist(db, redis, user)


async def remove_from_watchlist(
    db: AsyncSession, redis: Redis, user: User, symbol: str
) -> WatchlistResponse:
    wl = await _get_or_create_watchlist(db, user.id)
    item = await db.scalar(
        select(WatchlistItem).where(
            WatchlistItem.watchlist_id == wl.id, WatchlistItem.symbol == symbol.upper()
        )
    )
    if item:
        await db.delete(item)
        await db.commit()
    return await get_watchlist(db, redis, user)
