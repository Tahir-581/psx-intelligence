"""Unit tests for SEC 13F ingest batch logic."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text

from backend.config import settings
from scrapers.sec.ingest_13f import CoverPage, _compute_qoq, _flush_batch

TEST_CIK = "0000099999"
TEST_PERIOD = "2024-12-31"
PRIOR_PERIOD = "2024-09-30"
ACC_A = "0000099999-24-000001"
ACC_B = "0000099999-24-000002"
ACC_PRIOR = "0000099999-24-000010"
ACC_CURRENT = "0000099999-24-000011"


def _holding_item(accession: str, cusip: str = "037833100") -> dict:
    return {
        "accession": accession,
        "cik": TEST_CIK,
        "period": TEST_PERIOD,
        "nameOfIssuer": "Apple Inc",
        "titleOfClass": "COM",
        "cusip": cusip,
        "valueUsd": 1000,
        "shares": 10,
        "infotableSk": "",
    }


def _cover(accession: str) -> CoverPage:
    return CoverPage(
        accession_number=accession,
        cik=TEST_CIK,
        name="Test Ingest Fund",
        report_period=TEST_PERIOD,
        filed_at=TEST_PERIOD,
        form_type="13F-HR",
    )


def _cleanup(conn) -> None:
    conn.execute(text("DELETE FROM sec_holdings WHERE cik = :cik"), {"cik": TEST_CIK})
    conn.execute(text("DELETE FROM sec_filings_13f WHERE cik = :cik"), {"cik": TEST_CIK})
    conn.execute(text("DELETE FROM sec_filers WHERE cik = :cik"), {"cik": TEST_CIK})


@pytest.fixture
def db_engine():
    try:
        engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as exc:
        pytest.skip(f"Database unavailable: {exc}")


def test_cross_batch_supersede_skips_stale_holdings(db_engine) -> None:
    cover_map = {ACC_A: _cover(ACC_A), ACC_B: _cover(ACC_B)}
    processed: set[str] = set()
    superseded_accessions: set[str] = set()
    report_periods: set[str] = set()
    accession_totals: dict[str, int] = {}

    with db_engine.begin() as conn:
        _cleanup(conn)

        _flush_batch(
            conn,
            [_holding_item(ACC_A)],
            accession_totals,
            cover_map,
            processed,
            report_periods,
            superseded_accessions,
        )
        assert ACC_A in processed
        assert ACC_A not in superseded_accessions

        _flush_batch(
            conn,
            [_holding_item(ACC_B, "594918104")],
            accession_totals,
            cover_map,
            processed,
            report_periods,
            superseded_accessions,
        )
        assert ACC_A in superseded_accessions

        inserted = _flush_batch(
            conn,
            [_holding_item(ACC_A, "67066G104")],
            accession_totals,
            cover_map,
            processed,
            report_periods,
            superseded_accessions,
        )
        assert inserted == 0

        rows = conn.execute(
            text("SELECT accession_number FROM sec_holdings WHERE cik = :cik ORDER BY 1"),
            {"cik": TEST_CIK},
        ).fetchall()
        assert [row.accession_number for row in rows] == [ACC_B]

        _cleanup(conn)


def _seed_filer_and_filing(conn, accession: str, period: str) -> None:
    conn.execute(
        text("""
            INSERT INTO sec_filers (cik, name, investor_type, avatar_initials, avatar_color)
            VALUES (:cik, 'Test QoQ Fund', 'hedge_fund', 'TQ', 'blue')
            ON CONFLICT (cik) DO NOTHING
        """),
        {"cik": TEST_CIK},
    )
    conn.execute(
        text("""
            INSERT INTO sec_filings_13f (accession_number, cik, report_period, filed_at, form_type)
            VALUES (:acc, :cik, CAST(:period AS date), CAST(:period AS date), '13F-HR')
            ON CONFLICT (accession_number) DO NOTHING
        """),
        {"acc": accession, "cik": TEST_CIK, "period": period},
    )


def _insert_holding(
    conn,
    accession: str,
    period: str,
    issuer: str,
    cusip: str,
    shares: int,
) -> None:
    conn.execute(
        text("""
            INSERT INTO sec_holdings (
              accession_number, cik, report_period, name_of_issuer, cusip,
              title_of_class, value_usd, shares, portfolio_pct
            ) VALUES (
              :acc, :cik, CAST(:period AS date), :issuer, :cusip, 'COM', 1000, :shares, 10
            )
        """),
        {
            "acc": accession,
            "cik": TEST_CIK,
            "period": period,
            "issuer": issuer,
            "cusip": cusip,
            "shares": shares,
        },
    )


def test_compute_qoq_matched_new_and_changed(db_engine) -> None:
    with db_engine.begin() as conn:
        _cleanup(conn)
        _seed_filer_and_filing(conn, ACC_PRIOR, PRIOR_PERIOD)
        _seed_filer_and_filing(conn, ACC_CURRENT, TEST_PERIOD)
        _insert_holding(conn, ACC_PRIOR, PRIOR_PERIOD, "Apple Inc", "037833100", 100)
        _insert_holding(conn, ACC_PRIOR, PRIOR_PERIOD, "Alphabet Inc", "02079K305", 50)
        _insert_holding(conn, ACC_CURRENT, TEST_PERIOD, "Apple Inc", "037833100", 150)
        _insert_holding(conn, ACC_CURRENT, TEST_PERIOD, "Alphabet Inc", "02079K305", 50)
        _insert_holding(conn, ACC_CURRENT, TEST_PERIOD, "Microsoft Corp", "594918104", 25)

        prior = _compute_qoq(conn, TEST_PERIOD)
        assert prior == PRIOR_PERIOD

        rows = {
            row.name_of_issuer: row
            for row in conn.execute(
                text("""
                    SELECT name_of_issuer, shares, qoq_change_pct, is_new
                    FROM sec_holdings
                    WHERE cik = :cik AND report_period = CAST(:period AS date)
                    ORDER BY name_of_issuer
                """),
                {"cik": TEST_CIK, "period": TEST_PERIOD},
            )
        }
        assert float(rows["Alphabet Inc"].qoq_change_pct) == 0
        assert rows["Alphabet Inc"].is_new is False
        assert float(rows["Apple Inc"].qoq_change_pct) == 50
        assert rows["Apple Inc"].is_new is False
        assert float(rows["Microsoft Corp"].qoq_change_pct) == 100
        assert rows["Microsoft Corp"].is_new is True

        _cleanup(conn)
