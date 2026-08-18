"""SendGrid email delivery for alerts."""

from __future__ import annotations

import logging

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)


async def send_alert_email(*, to_email: str, subject: str, body: str) -> bool:
    if not settings.sendgrid_api_key:
        logger.warning("SENDGRID_API_KEY not set; skipping alert email to %s", to_email)
        return False
    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": settings.alerts_from_email},
        "subject": subject,
        "content": [{"type": "text/plain", "value": body}],
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {settings.sendgrid_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if resp.status_code >= 400:
                logger.error("SendGrid error %s: %s", resp.status_code, resp.text)
                return False
            return True
    except Exception as exc:
        logger.exception("SendGrid send failed: %s", exc)
        return False
