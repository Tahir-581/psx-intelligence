"""Ingest SEC Form 4 insider filings into sec_insiders."""

from __future__ import annotations

import json
import logging
import re

import httpx
from sqlalchemy import create_engine, text

from backend.config import settings

logger = logging.getLogger(__name__)


def _fetch_form4_atom(count: int) -> list[dict[str, str]]:
    url = (
        "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent"
        f"&type=4&dateb=&owner=include&count={count}&search_text=&output=atom"
    )
    with httpx.Client(timeout=60.0) as client:
        res = client.get(url, headers={"User-Agent": settings.sec_user_agent})
        res.raise_for_status()
        xml = res.text
    entries = xml.split("<entry>")[1:]
    results: list[dict[str, str]] = []
    for entry in entries:
        title_m = re.search(r"<title[^>]*>([^<]+)</title>", entry, re.I)
        updated_m = re.search(r"<updated>([^<]+)</updated>", entry)
        link_m = re.search(r'<link[^>]+href="([^"]+)"', entry)
        results.append({
            "title": title_m.group(1).strip() if title_m else "Form 4",
            "filedAt": updated_m.group(1) if updated_m else "",
            "link": link_m.group(1) if link_m else f"form4-{len(results)}",
        })
    return results


def _parse_form4_title(title: str) -> tuple[str, str, str | None]:
    parts = title.split(" - ")
    name = parts[0].strip() if parts else title
    rest = " - ".join(parts[1:]) if len(parts) > 1 else ""
    action = None
    if re.search(r"sell|sold|disposition", title, re.I):
        action = "sell"
    elif re.search(r"buy|purchase|acquired", title, re.I):
        action = "buy"
    company_m = re.search(r"\(([^)]+)\)", rest)
    company_name = company_m.group(1) if company_m else rest[:80]
    return name, company_name, action


def run_ingest_form4() -> dict:
    engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
    count = settings.sec_form4_count

    with engine.begin() as conn:
        run_id = conn.execute(
            text("""
                INSERT INTO sec_ingestion_runs (source, quarter_label, status)
                VALUES ('form4-atom', 'recent', 'running') RETURNING id
            """),
        ).scalar_one()

    try:
        logger.info("Fetching up to %s Form 4 atom entries from SEC...", count)
        entries = _fetch_form4_atom(count)
        logger.info("Fetched %s Form 4 entries", len(entries))
        inserted = 0
        with engine.begin() as conn:
            for entry in entries:
                name, company_name, action = _parse_form4_title(entry["title"])
                accession = (
                    entry["link"].split("/")[-1].replace("-index.htm", "")
                    if entry["link"]
                    else entry["link"]
                )
                result = conn.execute(
                    text("""
                        INSERT INTO sec_insiders (
                          name, company_name, form_type, filed_at, action, accession_number
                        ) VALUES (:name, :company, '4', CAST(COALESCE(:filed, NOW()) AS timestamptz), :action, :acc)
                        ON CONFLICT (accession_number, name, transaction_date, action, shares)
                        DO NOTHING RETURNING id
                    """),
                    {
                        "name": name,
                        "company": company_name,
                        "filed": entry["filedAt"] or None,
                        "action": action,
                        "acc": accession,
                    },
                )
                if result.first():
                    inserted += 1
            counts = {"fetched": len(entries), "inserted": inserted}
            conn.execute(
                text("""
                    UPDATE sec_ingestion_runs SET finished_at = NOW(), status = 'success',
                    row_counts = CAST(:counts AS jsonb) WHERE id = :id
                """),
                {"id": run_id, "counts": json.dumps(counts)},
            )
        logger.info("Inserted %s new Form 4 insider records", inserted)
        return {"status": "success", **counts}
    except Exception as exc:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE sec_ingestion_runs SET finished_at = NOW(), status = 'failed',
                    error_message = :msg WHERE id = :id
                """),
                {"id": run_id, "msg": str(exc)},
            )
        raise
