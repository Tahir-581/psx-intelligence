"""Cache invalidation for ticker-scoped keys after ingest."""

from __future__ import annotations

from redis.asyncio import Redis


async def invalidate_ticker_cache(redis: Redis, symbol: str) -> int:
    pattern = f"ticker:{symbol.upper()}:*"
    deleted = 0
    async for key in redis.scan_iter(match=pattern):
        await redis.delete(key)
        deleted += 1
    return deleted
