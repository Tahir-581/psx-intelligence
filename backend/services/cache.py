import json
from typing import Any

import redis as sync_redis
from redis.asyncio import Redis

from backend.config import settings


async def cache_get_json(redis: Redis, key: str) -> Any | None:
    raw = await redis.get(key)
    if not raw:
        return None
    return json.loads(raw)


async def cache_set_json(redis: Redis, key: str, value: Any, ttl: int) -> None:
    await redis.setex(key, ttl, json.dumps(value, default=str))


async def cache_delete_pattern(redis: Redis, pattern: str) -> int:
    count = 0
    async for key in redis.scan_iter(match=pattern):
        await redis.delete(key)
        count += 1
    return count


def flush_cache_pattern_sync(pattern: str) -> int:
    client = sync_redis.from_url(settings.redis_url, decode_responses=True)
    try:
        count = 0
        for key in client.scan_iter(match=pattern):
            client.delete(key)
            count += 1
        return count
    finally:
        client.close()
