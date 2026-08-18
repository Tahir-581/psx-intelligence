"""SEC Form 13F quarterly bulk ingest."""

from __future__ import annotations

import io
import json
import logging
import re
import time
import zipfile
from dataclasses import dataclass
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from backend.config import settings
from scrapers.sec.backfill_filer_summaries import backfill_filer_summaries
from scrapers.sec.ingest_utils import (
    avatar_color_for_cik,
    classify_investor_type,
    fetch_sec_buffer,
    get_field,
    initials_from_name,
    is_valid_cik,
    normalize_13f_value,
    parse_sec_date,
    parse_tsv_header,
    parse_tsv_line,
    pad_cik,
    resolve_latest_13f_zip_url,
)

logger = logging.getLogger(__name__)
BATCH_SIZE = 5000


@dataclass
class CoverPage:
    accession_number: str
    cik: str
    name: str
    report_period: str
    filed_at: str
    form_type: str


def _get_engine() -> Engine:
    return create_engine(settings.database_url_sync, pool_pre_ping=True)


def _read_zip_entry(zf: zipfile.ZipFile, pattern: re.Pattern[str]) -> str | None:
    for name in zf.namelist():
        if not name.endswith("/") and pattern.search(name):
            return zf.read(name).decode("utf-8", errors="replace")
    return None


def _parse_cover_pages(content: str) -> dict[str, CoverPage]:
    lines = [ln for ln in content.splitlines() if ln.strip()]
    if not lines:
        return {}
    header = parse_tsv_header(lines[0])
    result: dict[str, CoverPage] = {}
    for line in lines[1:]:
        row = parse_tsv_line(line)
        accession = get_field(row, header, "ACCESSION_NUMBER")
        if not accession:
            continue
        cik_raw = get_field(row, header, "CIK")
        cik = pad_cik(cik_raw) if cik_raw else ""
        name = get_field(row, header, "FILINGMANAGER_NAME") or get_field(row, header, "NAME")
        report_period = parse_sec_date(
            get_field(row, header, "REPORTCALENDARORQUARTER")
            or get_field(row, header, "REPORTCALENDARORQUARTERENDDATE")
        )
        filed_at = parse_sec_date(
            get_field(row, header, "FILING_DATE")
            or get_field(row, header, "FILINGDATE")
            or get_field(row, header, "SIGNATUREDATE")
            or get_field(row, header, "DATEREPORTED")
        )
        form_type = get_field(row, header, "FORM13FFILINGSREPORTTYPE") or "13F-HR"
        result[accession] = CoverPage(
            accession_number=accession,
            cik=cik,
            name=name,
            report_period=report_period,
            filed_at=filed_at or report_period,
            form_type=form_type,
        )
    return result


def _parse_submissions(content: str) -> dict[str, str]:
    lines = [ln for ln in content.splitlines() if ln.strip()]
    if not lines:
        return {}
    header = parse_tsv_header(lines[0])
    result: dict[str, str] = {}
    for line in lines[1:]:
        row = parse_tsv_line(line)
        accession = get_field(row, header, "ACCESSION_NUMBER")
        cik_raw = get_field(row, header, "CIK")
        cik = re.sub(r"\D", "", cik_raw).zfill(10)
        if is_valid_cik(cik):
            result[accession] = cik
    return result


def _upsert_filer_stub(conn: Any, cover: CoverPage) -> None:
    if not is_valid_cik(cover.cik):
        return
    conn.execute(
        text("""
            INSERT INTO sec_filers (cik, name, investor_type, avatar_initials, avatar_color)
            VALUES (:cik, :name, CAST(:itype AS sec_investor_type), :initials, :color)
            ON CONFLICT (cik) DO UPDATE SET
              name = CASE WHEN EXCLUDED.name <> '' THEN EXCLUDED.name ELSE sec_filers.name END,
              updated_at = NOW()
        """),
        {
            "cik": cover.cik,
            "name": cover.name or "Unknown filer",
            "itype": classify_investor_type(cover.name),
            "initials": initials_from_name(cover.name or "UN"),
            "color": avatar_color_for_cik(cover.cik),
        },
    )


def _lookup_prior_period(conn: Any, report_period: str) -> str | None:
    return conn.execute(
        text("""
            SELECT report_period::text FROM (
              SELECT DISTINCT report_period FROM sec_holdings
              WHERE report_period < CAST(:period AS date)
            ) p ORDER BY report_period DESC LIMIT 1
        """),
        {"period": report_period},
    ).scalar_one_or_none()


def _compute_qoq(conn: Any, report_period: str) -> str | None:
    """Compute QoQ change for one report period. Returns prior period or None."""
    prior = _lookup_prior_period(conn, report_period)
    if not prior:
        return None
    conn.execute(
        text("""
            UPDATE sec_holdings AS cur
            SET
              qoq_change_pct = CASE
                WHEN prev.id IS NULL THEN 100
                WHEN prev.shares = 0 THEN 0
                ELSE LEAST(999999.9999::numeric, GREATEST(-999999.9999::numeric,
                  ROUND(((cur.shares - prev.shares)::numeric / prev.shares) * 100, 4)))
              END,
              is_new = (prev.id IS NULL)
            FROM sec_holdings AS base
            LEFT JOIN sec_holdings AS prev
              ON prev.cik = base.cik
             AND prev.report_period = CAST(:prior AS date)
             AND prev.cusip = base.cusip
             AND prev.name_of_issuer = base.name_of_issuer
            WHERE cur.id = base.id
              AND base.report_period = CAST(:period AS date)
        """),
        {"period": report_period, "prior": prior},
    )
    return prior


def _compute_qoq_all_periods(engine: Engine, report_periods: set[str]) -> None:
    periods = sorted(report_periods)
    total = len(periods)
    logger.info("Computing QoQ changes for %s report periods...", total)
    for idx, period in enumerate(periods, start=1):
        period_start = time.monotonic()
        with engine.begin() as conn:
            prior = _compute_qoq(conn, period)
        if prior:
            logger.info(
                "QoQ %s/%s: %s vs %s (%.1fs)",
                idx,
                total,
                period,
                prior,
                time.monotonic() - period_start,
            )
        else:
            logger.info(
                "QoQ %s/%s: %s (no prior period, skipped, %.1fs)",
                idx,
                total,
                period,
                time.monotonic() - period_start,
            )


def _flush_batch(
    conn: Any,
    batch: list[dict[str, Any]],
    accession_totals: dict[str, int],
    cover_map: dict[str, CoverPage],
    processed: set[str],
    report_periods: set[str],
    superseded_accessions: set[str],
) -> int:
    deduped: dict[str, dict[str, Any]] = {}
    for item in batch:
        if not is_valid_cik(item["cik"]):
            continue
        key = f"{item['accession']}|{item['cusip']}|{item['nameOfIssuer']}|{item['titleOfClass']}"
        if key in deduped:
            deduped[key]["valueUsd"] += item["valueUsd"]
            deduped[key]["shares"] += item["shares"]
        else:
            deduped[key] = dict(item)

    for item in deduped.values():
        total = accession_totals.get(item["accession"], item["valueUsd"])
        item["portfolioPct"] = (item["valueUsd"] / total * 100) if total > 0 else 0

    accessions_in_batch = {item["accession"] for item in deduped.values()}

    for accession in accessions_in_batch:
        if accession in processed:
            continue
        cover = cover_map.get(accession)
        sample = next((d for d in deduped.values() if d["accession"] == accession), None)
        if not cover or not sample or not is_valid_cik(sample["cik"]):
            continue
        _upsert_filer_stub(conn, cover)
        replaced = conn.execute(
            text("""
                DELETE FROM sec_filings_13f
                WHERE cik = :cik AND report_period = CAST(:period AS date) AND accession_number <> :acc
                RETURNING accession_number
            """),
            {"cik": sample["cik"], "period": sample["period"], "acc": accession},
        )
        for row in replaced:
            superseded_accessions.add(row.accession_number)
        conn.execute(
            text("""
                INSERT INTO sec_filings_13f (accession_number, cik, report_period, filed_at, form_type, quarter_label)
                VALUES (:acc, :cik, CAST(:period AS date), CAST(:filed AS date), :form, :label)
                ON CONFLICT (accession_number) DO UPDATE SET
                  report_period = EXCLUDED.report_period, filed_at = EXCLUDED.filed_at
            """),
            {
                "acc": accession,
                "cik": sample["cik"],
                "period": sample["period"],
                "filed": cover.filed_at or sample["period"],
                "form": cover.form_type,
                "label": sample["period"],
            },
        )
        conn.execute(
            text("DELETE FROM sec_holdings WHERE accession_number = :acc"),
            {"acc": accession},
        )
        processed.add(accession)
        report_periods.add(sample["period"])

    inserted = 0
    for item in deduped.values():
        if item["accession"] in superseded_accessions:
            continue
        if item["accession"] not in processed:
            continue
        conn.execute(
            text("""
                INSERT INTO sec_holdings (
                  accession_number, cik, report_period, name_of_issuer, cusip,
                  title_of_class, value_usd, shares, portfolio_pct, infotable_sk
                ) VALUES (
                  :acc, :cik, CAST(:period AS date), :issuer, :cusip, :title,
                  :value, :shares, :pct, :sk
                )
                ON CONFLICT (accession_number, cusip, name_of_issuer, title_of_class)
                DO UPDATE SET value_usd = EXCLUDED.value_usd, shares = EXCLUDED.shares,
                  portfolio_pct = EXCLUDED.portfolio_pct
            """),
            {
                "acc": item["accession"],
                "cik": item["cik"],
                "period": item["period"],
                "issuer": item["nameOfIssuer"],
                "cusip": item["cusip"],
                "title": item["titleOfClass"],
                "value": item["valueUsd"],
                "shares": item["shares"],
                "pct": item["portfolioPct"],
                "sk": int(item["infotableSk"]) if item.get("infotableSk") else None,
            },
        )
        inserted += 1
    return inserted


def ingest_zip_buffer(engine: Engine, buffer: bytes, quarter_label: str) -> dict[str, int]:
    parse_start = time.monotonic()
    zf = zipfile.ZipFile(io.BytesIO(buffer))
    submission_text = _read_zip_entry(zf, re.compile(r"SUBMISSION\.tsv$", re.I))
    cover_text = _read_zip_entry(zf, re.compile(r"COVERPAGE\.tsv$", re.I))
    info_text = _read_zip_entry(zf, re.compile(r"INFOTABLE\.tsv$", re.I))
    if not cover_text or not info_text:
        raise RuntimeError("ZIP missing COVERPAGE.tsv or INFOTABLE.tsv")

    submission_map = _parse_submissions(submission_text) if submission_text else {}
    cover_map = _parse_cover_pages(cover_text)
    for accession, cover in cover_map.items():
        if not cover.cik and accession in submission_map:
            cover.cik = submission_map[accession]

    info_lines = [ln for ln in info_text.splitlines() if ln.strip()]
    info_header = parse_tsv_header(info_lines[0])
    infotable_rows = len(info_lines) - 1
    logger.info(
        "Parsed ZIP for %s: %s cover pages, %s INFOTABLE rows, %s submissions (%.1fs)",
        quarter_label,
        len(cover_map),
        f"{infotable_rows:,}",
        len(submission_map),
        time.monotonic() - parse_start,
    )

    processed: set[str] = set()
    superseded_accessions: set[str] = set()
    report_periods: set[str] = set()
    accession_totals: dict[str, int] = {}
    batch: list[dict[str, Any]] = []
    holdings_inserted = 0
    batch_num = 0
    ingest_start = time.monotonic()

    for line in info_lines[1:]:
        row = parse_tsv_line(line)
        accession = get_field(row, info_header, "ACCESSION_NUMBER")
        if not accession:
            continue
        cover = cover_map.get(accession)
        if not cover or not cover.cik or not cover.report_period or not is_valid_cik(cover.cik):
            continue
        name_of_issuer = get_field(row, info_header, "NAMEOFISSUER")
        cusip = get_field(row, info_header, "CUSIP")
        if not name_of_issuer and not cusip:
            continue
        value_usd = normalize_13f_value(
            get_field(row, info_header, "VALUE"), cover.report_period
        )
        shares_raw = get_field(row, info_header, "SSHPRNAMT").replace(",", "")
        shares = int(float(shares_raw)) if shares_raw else 0
        accession_totals[accession] = accession_totals.get(accession, 0) + value_usd
        batch.append({
            "accession": accession,
            "cik": cover.cik,
            "period": cover.report_period,
            "nameOfIssuer": name_of_issuer,
            "titleOfClass": get_field(row, info_header, "TITLEOFCLASS"),
            "cusip": cusip,
            "valueUsd": value_usd,
            "shares": shares,
            "infotableSk": get_field(row, info_header, "INFOTABLE_SK"),
        })
        if len(batch) >= BATCH_SIZE:
            batch_num += 1
            with engine.begin() as conn:
                inserted = _flush_batch(
                    conn, batch, accession_totals, cover_map, processed, report_periods,
                    superseded_accessions,
                )
            holdings_inserted += inserted
            logger.info(
                "Batch %s: +%s holdings (%s total, %s filings)",
                batch_num,
                f"{inserted:,}",
                f"{holdings_inserted:,}",
                len(processed),
            )
            batch = []

    if batch:
        batch_num += 1
        with engine.begin() as conn:
            inserted = _flush_batch(
                conn, batch, accession_totals, cover_map, processed, report_periods,
                superseded_accessions,
            )
        holdings_inserted += inserted
        logger.info(
            "Batch %s: +%s holdings (%s total, %s filings)",
            batch_num,
            f"{inserted:,}",
            f"{holdings_inserted:,}",
            len(processed),
        )

    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE sec_holdings h SET ticker = m.ticker
                FROM sec_cusip_ticker_map m
                WHERE h.cusip = m.cusip AND (h.ticker IS NULL OR h.ticker = '')
            """)
        )
    _compute_qoq_all_periods(engine, report_periods)

    logger.info(
        "DB ingest finished in %.1fs (%s batches)",
        time.monotonic() - ingest_start,
        batch_num,
    )

    logger.info("Backfilling filer summaries from holdings...")
    backfill = backfill_filer_summaries(engine)
    logger.info("Backfilled %s filer summaries", backfill["updated"])
    return {
        "filings": len(processed),
        "holdings": holdings_inserted,
        "periods": len(report_periods),
        "filersBackfilled": backfill["updated"],
    }


def run_ingest_13f(zip_url: str | None = None, quarter_label: str | None = None) -> dict[str, Any]:
    run_start = time.monotonic()
    engine = _get_engine()
    if zip_url:
        url, label = zip_url, quarter_label or "custom"
    else:
        logger.info("Resolving latest 13F ZIP URL from SEC...")
        url, label = resolve_latest_13f_zip_url()
    logger.info("Quarter: %s", label)
    logger.info("Source URL: %s", url)

    with engine.begin() as conn:
        run_id = conn.execute(
            text("""
                INSERT INTO sec_ingestion_runs (source, quarter_label, status)
                VALUES (:source, :label, 'running') RETURNING id
            """),
            {"source": url, "label": label},
        ).scalar_one()
    logger.info("Ingestion run id=%s started", run_id)

    try:
        download_start = time.monotonic()
        logger.info("Downloading 13F dataset...")
        buffer = fetch_sec_buffer(url)
        size_mb = len(buffer) / (1024 * 1024)
        logger.info(
            "Download complete (%.1f MB, %.1fs)",
            size_mb,
            time.monotonic() - download_start,
        )
        counts = ingest_zip_buffer(engine, buffer, label)
        with engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE sec_ingestion_runs SET finished_at = NOW(), status = 'success',
                    row_counts = CAST(:counts AS jsonb) WHERE id = :id
                """),
                {"id": run_id, "counts": json.dumps(counts)},
            )
        logger.info(
            "Done: %s filings, %s holdings, %s periods (%.1fs total)",
            f"{counts['filings']:,}",
            f"{counts['holdings']:,}",
            counts["periods"],
            time.monotonic() - run_start,
        )
        return {"status": "success", "quarter": label, **counts}
    except Exception as exc:
        logger.error("Ingest failed after %.1fs: %s", time.monotonic() - run_start, exc)
        with engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE sec_ingestion_runs SET finished_at = NOW(), status = 'failed',
                    error_message = :msg WHERE id = :id
                """),
                {"id": run_id, "msg": str(exc)},
            )
        raise
