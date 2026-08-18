"""Daily digest email for watchlist users — 08:00 PKT."""

from __future__ import annotations

import logging

from sqlalchemy import select

from backend.config import settings
from backend.services.ratios import get_sync_session
from backend.models.user import User
from backend.models.notification_prefs import UserNotificationPrefs

logger = logging.getLogger(__name__)


def run_daily_digest() -> dict:
    if not settings.sendgrid_api_key:
        return {"sent": 0, "skipped": "sendgrid_not_configured"}
    session = get_sync_session()
    try:
        users = session.execute(
            select(User, UserNotificationPrefs)
            .outerjoin(UserNotificationPrefs, UserNotificationPrefs.user_id == User.id)
            .where(User.email.isnot(None))
        ).all()
        sent = 0
        for user, prefs in users:
            if prefs and not prefs.digest_enabled:
                continue
            if _send_digest_email(user.email):
                sent += 1
        return {"sent": sent}
    finally:
        session.close()


def _send_digest_email(email: str) -> bool:
    try:
        import httpx

        resp = httpx.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={
                "Authorization": f"Bearer {settings.sendgrid_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "personalizations": [{"to": [{"email": email}]}],
                "from": {"email": settings.alerts_from_email},
                "subject": "PSX Intelligence — Daily Digest",
                "content": [
                    {
                        "type": "text/plain",
                        "value": "Your daily PSX watchlist digest. Visit the dashboard for details.",
                    }
                ],
            },
            timeout=30,
        )
        return resp.status_code < 400
    except Exception as exc:
        logger.warning("Digest email failed for %s: %s", email, exc)
        return False
