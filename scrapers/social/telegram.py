"""Telegram channel scraper (stretch — daily aggregation)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def run_scrape_telegram() -> dict:
    """Telegram public channel monitoring when TELEGRAM_BOT_TOKEN is set."""
    from backend.config import settings

    if not settings.telegram_bot_token:
        logger.info("TELEGRAM_BOT_TOKEN not set — skipping")
        return {"ingested": 0, "linked": 0, "status": "skipped"}
    try:
        import httpx

        resp = httpx.get(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/getUpdates",
            timeout=15,
        )
        if resp.status_code != 200:
            return {"ingested": 0, "linked": 0, "status": "error", "detail": resp.text[:200]}
        return {"ingested": len(resp.json().get("result", [])), "linked": 0, "status": "ok"}
    except Exception as exc:
        logger.warning("Telegram scrape failed: %s", exc)
        return {"ingested": 0, "linked": 0, "status": "error", "detail": str(exc)}
