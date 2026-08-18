"""Reddit scraper (stretch — daily task)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def run_scrape_reddit() -> dict:
    """Reddit subreddit search when REDDIT_CLIENT_ID is set."""
    from backend.config import settings

    if not settings.reddit_client_id or not settings.reddit_client_secret:
        logger.info("Reddit credentials not set — skipping")
        return {"ingested": 0, "linked": 0, "status": "skipped"}
    try:
        import httpx

        resp = httpx.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=(settings.reddit_client_id, settings.reddit_client_secret),
            data={"grant_type": "client_credentials"},
            headers={"User-Agent": settings.reddit_user_agent},
            timeout=15,
        )
        if resp.status_code != 200:
            return {"ingested": 0, "linked": 0, "status": "error"}
        return {"ingested": 0, "linked": 0, "status": "authenticated"}
    except Exception as exc:
        logger.warning("Reddit scrape failed: %s", exc)
        return {"ingested": 0, "linked": 0, "status": "error", "detail": str(exc)}
