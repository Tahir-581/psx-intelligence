"""SEC EFTS delta sync for recent 13F-HR filings."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import create_engine, text

from backend.config import settings
from scrapers.sec.ingest_utils import initials_from_name, pad_cik

logger = logging.getLogger(__name__)


def _date_minus_days(days: int) -> str:
    return (datetime.now(UTC) - timedelta(days=days)).strftime("%Y-%m-%d")


def _fetch_recent_13f(days: int) -> list[dict[str, str]]:
    startdt = _date_minus_days(days)
    url = (
        "https://efts.sec.gov/LATEST/search-index"
        f'?q=%2213F-HR%22&dateRange=custom&startdt={startdt}&forms=13F-HR'
        "&_source=file_date,entity_name,cik,file_num,period_of_report"
    )
    with httpx.Client(timeout=60.0) as client:
        res = client.get(url, headers={"User-Agent": settings.sec_user_agent})
        res.raise_for_status()
        data = res.json()
    hits = data.get("hits", {}).get("hits", [])
    return [h.get("_source", {}) for h in hits]


def run_ingest_delta() -> dict:
    engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
    days = settings.sec_ingest_delta_days
    logger.info("Fetching 13F-HR filings from last %s days...", days)

    with engine.begin() as conn:
        run_id = conn.execute(
            text("""
                INSERT INTO sec_ingestion_runs (source, quarter_label, status)
                VALUES ('efts-delta', :label, 'running') RETURNING id
            """),
            {"label": f"last-{days}-days"},
        ).scalar_one()

    try:
        filings = _fetch_recent_13f(days)
        logger.info("Fetched %s recent 13F-HR filings from SEC", len(filings))
    except Exception as exc:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE sec_ingestion_runs SET finished_at = NOW(), status = 'skipped',
                    error_message = :msg WHERE id = :id
                """),
                {"id": run_id, "msg": str(exc)},
            )
        return {"status": "skipped", "error": str(exc)}

    new_filers = 0
    known_filers = 0
    with engine.begin() as conn:
        for src in filings:
            cik = pad_cik(src.get("cik", ""))
            name = src.get("entity_name", "Unknown")
            if not cik:
                continue
            existing = conn.execute(
                text("SELECT cik FROM sec_filers WHERE cik = :cik"), {"cik": cik}
            ).first()
            filed = (src.get("file_date") or "")[:10]
            if existing:
                known_filers += 1
                conn.execute(
                    text("""
                        UPDATE sec_filers SET last_filing_date = GREATEST(
                          COALESCE(last_filing_date, '1900-01-01'::date), CAST(:filed AS date)
                        ), updated_at = NOW() WHERE cik = :cik
                    """),
                    {"cik": cik, "filed": filed or "1900-01-01"},
                )
            else:
                new_filers += 1
                conn.execute(
                    text("""
                        INSERT INTO sec_filers (cik, name, investor_type, last_filing_date,
                          avatar_initials, avatar_color)
                        VALUES (:cik, :name, 'unknown', CAST(:filed AS date), :initials, 'blue')
                        ON CONFLICT (cik) DO NOTHING
                    """),
                    {
                        "cik": cik,
                        "name": name,
                        "filed": filed or None,
                        "initials": initials_from_name(name),
                    },
                )

        counts = {"eftsFilings": len(filings), "knownFilers": known_filers, "newFilers": new_filers}
        conn.execute(
            text("""
                UPDATE sec_ingestion_runs SET finished_at = NOW(), status = 'success',
                row_counts = CAST(:counts AS jsonb) WHERE id = :id
            """),
            {"id": run_id, "counts": json.dumps(counts)},
        )
    logger.info(
        "Delta sync complete: %s filings, %s new filers, %s known filers",
        len(filings),
        new_filers,
        known_filers,
    )
    return {"status": "success", **counts}
