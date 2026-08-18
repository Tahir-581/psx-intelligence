"""B2 archive service — uploads raw scrape payloads when configured."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.ingest import IngestArchive


def archive_content(
    session: Session,
    *,
    scraper_name: str,
    content: bytes,
    symbol: str | None = None,
) -> dict:
    if not settings.b2_application_key:
        return {"archived": False, "reason": "b2_not_configured"}
    content_hash = hashlib.sha256(content).hexdigest()
    key = f"{scraper_name}/{symbol or 'global'}/{content_hash[:16]}.bin"
    try:
        _upload_b2(key, content)
    except Exception as exc:
        return {"archived": False, "error": str(exc)}
    session.add(
        IngestArchive(
            scraper_name=scraper_name,
            symbol=symbol,
            b2_key=key,
            content_hash=content_hash,
            scraped_at=datetime.now(UTC),
        )
    )
    session.commit()
    return {"archived": True, "b2_key": key}


def _upload_b2(key: str, content: bytes) -> None:
    import httpx

    auth_url = f"{settings.b2_endpoint}/b2api/v2/b2_authorize_account"
    resp = httpx.get(auth_url, auth=(settings.b2_application_key_id, settings.b2_application_key))
    resp.raise_for_status()
    data = resp.json()
    upload_url = data["uploadUrl"]
    upload_auth = data["authorizationToken"]
    upload_resp = httpx.post(
        upload_url,
        headers={
            "Authorization": upload_auth,
            "X-Bz-File-Name": key,
            "Content-Type": "application/octet-stream",
            "X-Bz-Content-Sha1": "do_not_verify",
        },
        content=content,
        timeout=60,
    )
    upload_resp.raise_for_status()
