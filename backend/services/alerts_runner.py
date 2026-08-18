"""Sync Celery entrypoint for alert evaluation."""

from __future__ import annotations

import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from backend.config import settings
from backend.database import async_session_factory, get_redis
from backend.services.alerts import evaluate_all_alerts, trigger_event_alerts_for_symbols


def _market_open_now() -> bool:
    tz = ZoneInfo(settings.market_timezone)
    now = datetime.now(tz)
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    return 9 * 60 + 30 <= minutes <= 15 * 60 + 30


async def _run_evaluate(event_only: bool) -> dict:
    redis = await get_redis()
    async with async_session_factory() as db:
        return await evaluate_all_alerts(db, redis, event_only=event_only)


def run_evaluate_alerts() -> dict:
    event_only = not _market_open_now()
    return asyncio.run(_run_evaluate(event_only))


async def _run_event_hook(symbols: list[str]) -> int:
    redis = await get_redis()
    async with async_session_factory() as db:
        return await trigger_event_alerts_for_symbols(db, redis, symbols)


def run_event_alerts_hook(symbols: list[str]) -> int:
    return asyncio.run(_run_event_hook(symbols))
