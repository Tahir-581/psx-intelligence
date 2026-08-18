"""SEC filer query layer — ported from smart-money-tracker lib/filer-queries.ts."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from scrapers.sec.edgar import (
    MOCK_INVESTMENTS,
    avatar_color_for_cik,
    get_sector_for_ticker,
    initials_from_name,
    strip_cik,
)
from scrapers.sec.ingest_utils import pad_cik


def _row_to_investor(row: Any) -> dict[str, Any]:
    inv_type = row.investor_type
    if inv_type == "unknown":
        inv_type = "hedge_fund"
    return {
        "cik": strip_cik(row.cik),
        "name": row.name,
        "type": inv_type,
        "aum": int(row.total_portfolio_value),
        "holdingsCount": row.holdings_count,
        "lastFilingDate": str(row.last_filing_date) if row.last_filing_date else "",
        "ytdChange": 0,
        "topTicker": row.top_ticker or "",
        "topPct": float(row.top_pct),
        "avatarInitials": initials_from_name(row.name),
        "avatarColor": avatar_color_for_cik(row.cik),
    }


def _row_to_holding(row: Any) -> dict[str, Any]:
    ticker = (row.ticker or "").strip() or row.cusip[:6] or row.name_of_issuer[:6].upper()
    return {
        "ticker": ticker,
        "companyName": row.name_of_issuer,
        "value": int(row.value_usd),
        "shares": int(row.shares),
        "portfolioPct": float(row.portfolio_pct),
        "qoqChange": float(row.qoq_change_pct),
        "isNew": bool(row.is_new),
    }


async def has_filer_data(db: AsyncSession) -> bool:
    result = await db.execute(text("SELECT COUNT(*) AS count FROM sec_filers"))
    return int(result.scalar_one()) > 0


async def _query_period_stats(
    db: AsyncSession,
    cik: str,
    report_period: str,
    q: str = "",
    changes_only: bool = False,
) -> dict[str, Any]:
    conditions = ["cik = :cik", "report_period = CAST(:period AS date)"]
    params: dict[str, Any] = {"cik": cik, "period": report_period}
    if q:
        conditions.append(
            "(name_of_issuer ILIKE :q OR COALESCE(ticker, '') ILIKE :q OR cusip ILIKE :q)"
        )
        params["q"] = f"%{q}%"
    if changes_only:
        conditions.append("(is_new = true OR qoq_change_pct <> 0)")
    where = " AND ".join(conditions)

    agg = await db.execute(
        text(f"""
            SELECT COALESCE(SUM(value_usd), 0) AS total_value,
                   COUNT(*) AS holdings_count,
                   (SELECT COALESCE(ticker, LEFT(cusip, 6)) FROM sec_holdings
                    WHERE {where} ORDER BY value_usd DESC LIMIT 1) AS top_ticker,
                   (SELECT portfolio_pct FROM sec_holdings
                    WHERE {where} ORDER BY portfolio_pct DESC LIMIT 1) AS top_pct
            FROM sec_holdings WHERE {where}
        """),
        params,
    )
    row = agg.one()
    top5 = await db.execute(
        text(f"""
            SELECT portfolio_pct FROM sec_holdings
            WHERE {where} ORDER BY portfolio_pct DESC LIMIT 5
        """),
        params,
    )
    top5_sum = round(sum(float(r.portfolio_pct) for r in top5), 1)
    return {
        "totalValue": int(row.total_value),
        "holdingsCount": int(row.holdings_count),
        "top5Concentration": top5_sum,
        "topTicker": row.top_ticker or "",
        "topPct": float(row.top_pct or 0),
    }


def _holdings_order_by(sort: str, order: str) -> str:
    direction = "ASC" if order == "asc" else "DESC"
    mapping = {
        "name": f"name_of_issuer {direction}",
        "ticker": f"COALESCE(ticker, cusip) {direction}",
        "pct": f"portfolio_pct {direction}",
        "qoq": f"qoq_change_pct {direction}",
        "shares": f"shares {direction}",
    }
    return mapping.get(sort, f"value_usd {direction}")


async def query_investors(
    db: AsyncSession,
    *,
    q: str | None = None,
    investor_type: str | None = None,
    sort: str = "aum",
    page: int = 1,
    limit: int = 50,
) -> dict[str, Any]:
    page = max(1, page)
    limit = min(100, max(1, limit))
    offset = (page - 1) * limit
    query_text = (q or "").strip()
    type_filter = investor_type if investor_type and investor_type != "all" else None

    order_by = {
        "name": "name ASC",
        "holdings": "holdings_count DESC",
        "filed": "last_filing_date DESC NULLS LAST",
    }.get(sort, "total_portfolio_value DESC")

    conditions: list[str] = []
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if query_text:
        conditions.append("search_vector @@ plainto_tsquery('english', :q)")
        params["q"] = query_text
    if type_filter:
        conditions.append("investor_type = CAST(:itype AS sec_investor_type)")
        params["itype"] = type_filter
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    count_row = await db.execute(
        text(f"SELECT COUNT(*) AS count FROM sec_filers {where}"), params
    )
    sum_row = await db.execute(
        text(f"SELECT COALESCE(SUM(total_portfolio_value), 0) AS total FROM sec_filers {where}"),
        params,
    )
    rows = await db.execute(
        text(f"""
            SELECT cik, name, investor_type::text, total_portfolio_value, holdings_count,
                   last_filing_date, top_ticker, top_pct
            FROM sec_filers {where}
            ORDER BY {order_by}
            LIMIT :limit OFFSET :offset
        """),
        params,
    )
    return {
        "investors": [_row_to_investor(r) for r in rows],
        "total": int(count_row.scalar_one()),
        "page": page,
        "limit": limit,
        "totalAum": int(sum_row.scalar_one()),
    }


async def query_investor_profile(db: AsyncSession, cik: str) -> dict[str, Any] | None:
    padded = pad_cik(cik)
    filer = await db.execute(
        text("""
            SELECT cik, name, investor_type::text, total_portfolio_value, holdings_count,
                   last_filing_date, last_report_period, top_ticker, top_pct
            FROM sec_filers WHERE cik = :cik
        """),
        {"cik": padded},
    )
    row = filer.first()
    if not row:
        return None

    period_rows = await db.execute(
        text("""
            SELECT DISTINCT report_period::text
            FROM sec_holdings WHERE cik = :cik
            ORDER BY report_period DESC LIMIT 8
        """),
        {"cik": padded},
    )
    periods = [r.report_period for r in period_rows]
    latest_period = periods[0] if periods else (
        str(row.last_report_period) if row.last_report_period else None
    )

    aum = int(row.total_portfolio_value)
    holdings_count = row.holdings_count
    top_ticker = row.top_ticker or ""
    top_pct = float(row.top_pct)
    top5_concentration = 0.0

    if latest_period:
        needs_fallback = aum == 0 or holdings_count == 0 or not top_ticker
        if needs_fallback:
            stats = await _query_period_stats(db, padded, latest_period)
            if stats["totalValue"] > 0 or stats["holdingsCount"] > 0:
                aum = stats["totalValue"]
                holdings_count = stats["holdingsCount"]
                top_ticker = stats["topTicker"] or top_ticker
                top_pct = stats["topPct"] or top_pct
                top5_concentration = stats["top5Concentration"]
        else:
            top5 = await db.execute(
                text("""
                    SELECT portfolio_pct FROM sec_holdings
                    WHERE cik = :cik AND report_period = CAST(:period AS date)
                    ORDER BY portfolio_pct DESC LIMIT 5
                """),
                {"cik": padded, "period": latest_period},
            )
            top5_concentration = round(sum(float(r.portfolio_pct) for r in top5), 1)

    base = _row_to_investor(row)
    return {
        **base,
        "aum": aum,
        "holdingsCount": holdings_count,
        "topTicker": top_ticker,
        "topPct": top_pct,
        "holdings": [],
        "totalHoldings": holdings_count,
        "top5Concentration": top5_concentration,
        "quarterlyTurnover": 0,
        "description": f"{base['name']} · CIK {base['cik']} · 13F filer",
        "reportPeriods": periods,
        "latestReportPeriod": latest_period,
    }


async def query_holdings(
    db: AsyncSession,
    *,
    cik: str,
    period: str | None = None,
    page: int = 1,
    limit: int = 50,
    sort: str = "value",
    order: str = "desc",
    q: str | None = None,
    changes_only: bool = False,
) -> dict[str, Any]:
    padded = pad_cik(cik)
    page = max(1, page)
    limit = min(200, max(1, limit))
    offset = (page - 1) * limit
    query_text = (q or "").strip()

    period_rows = await db.execute(
        text("""
            SELECT DISTINCT report_period::text FROM sec_holdings
            WHERE cik = :cik ORDER BY report_period DESC
        """),
        {"cik": padded},
    )
    periods = [r.report_period for r in period_rows]
    report_period = period if period and period in periods else (periods[0] if periods else "")

    empty_summary = {"totalValue": 0, "holdingsCount": 0, "top5Concentration": 0}
    if not report_period:
        return {
            "holdings": [], "total": 0, "page": page, "limit": limit,
            "reportPeriod": "", "periods": periods, "summary": empty_summary,
        }

    conditions = ["cik = :cik", "report_period = CAST(:period AS date)"]
    params: dict[str, Any] = {"cik": padded, "period": report_period, "limit": limit, "offset": offset}
    if query_text:
        conditions.append(
            "(name_of_issuer ILIKE :q OR COALESCE(ticker, '') ILIKE :q OR cusip ILIKE :q)"
        )
        params["q"] = f"%{query_text}%"
    if changes_only:
        conditions.append("(is_new = true OR qoq_change_pct <> 0)")
    where = " AND ".join(conditions)
    order_by = _holdings_order_by(sort, order)

    period_stats = await _query_period_stats(
        db, padded, report_period, query_text, changes_only
    )
    summary = {
        "totalValue": period_stats["totalValue"],
        "holdingsCount": period_stats["holdingsCount"],
        "top5Concentration": period_stats["top5Concentration"],
    }

    count_row = await db.execute(
        text(f"SELECT COUNT(*) FROM sec_holdings WHERE {where}"), params
    )
    rows = await db.execute(
        text(f"""
            SELECT ticker, name_of_issuer, cusip, value_usd, shares,
                   portfolio_pct, qoq_change_pct, is_new
            FROM sec_holdings WHERE {where}
            ORDER BY {order_by}
            LIMIT :limit OFFSET :offset
        """),
        params,
    )
    return {
        "holdings": [_row_to_holding(r) for r in rows],
        "total": int(count_row.scalar_one()),
        "page": page,
        "limit": limit,
        "reportPeriod": report_period,
        "periods": periods,
        "summary": summary,
    }


async def query_investment_changes(
    db: AsyncSession,
    *,
    action: str | None = None,
    sector: str | None = None,
    page: int = 1,
    limit: int = 50,
) -> dict[str, Any]:
    page = max(1, page)
    limit = min(100, max(1, limit))
    offset = (page - 1) * limit

    latest = await db.execute(
        text("SELECT MAX(report_period)::text AS report_period FROM sec_holdings")
    )
    latest_period = latest.scalar_one_or_none()
    if not latest_period:
        return {"investments": [], "total": 0, "page": page, "limit": limit}

    action_clause = ""
    if action == "new":
        action_clause = "AND h.is_new = true"
    elif action == "increased":
        action_clause = "AND h.qoq_change_pct > 0 AND h.is_new = false"
    elif action == "reduced":
        action_clause = "AND h.qoq_change_pct < 0"
    elif action == "exited":
        action_clause = "AND false"

    base_where = (
        f"h.report_period = CAST(:period AS date) "
        f"AND (h.is_new = true OR h.qoq_change_pct <> 0) {action_clause}"
    )
    params: dict[str, Any] = {"period": latest_period, "limit": limit, "offset": offset}

    count_row = await db.execute(
        text(f"""
            SELECT COUNT(*) FROM sec_holdings h
            JOIN sec_filers f ON f.cik = h.cik WHERE {base_where}
        """),
        params,
    )
    rows = await db.execute(
        text(f"""
            SELECT h.cik, f.name AS investor_name, f.investor_type::text, h.ticker,
                   h.name_of_issuer, h.value_usd, h.shares, h.portfolio_pct,
                   h.qoq_change_pct, h.is_new, f.last_filing_date, h.accession_number
            FROM sec_holdings h
            JOIN sec_filers f ON f.cik = h.cik
            WHERE {base_where}
            ORDER BY ABS(h.qoq_change_pct) DESC, h.value_usd DESC
            LIMIT :limit OFFSET :offset
        """),
        params,
    )

    investments: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        ticker = row.ticker or row.name_of_issuer[:6].upper()
        sec = get_sector_for_ticker(ticker)
        if sector and sector != "all" and sec != sector:
            continue
        act = "new" if row.is_new else ("increased" if float(row.qoq_change_pct) > 0 else "reduced")
        investments.append({
            "id": f"db-{row.accession_number}-{i}",
            "investorName": row.investor_name,
            "investorCik": strip_cik(row.cik),
            "investorType": row.investor_type if row.investor_type != "unknown" else "hedge_fund",
            "formType": "13F",
            "ticker": ticker,
            "companyName": row.name_of_issuer,
            "filedAt": str(row.last_filing_date) if row.last_filing_date else latest_period,
            "amount": int(row.value_usd),
            "shares": int(row.shares),
            "action": act,
            "portfolioPct": float(row.portfolio_pct),
            "accessionNo": row.accession_number,
            "avatarInitials": initials_from_name(row.investor_name),
            "avatarColor": avatar_color_for_cik(row.cik),
            "sector": sec,
        })

    return {
        "investments": investments,
        "total": int(count_row.scalar_one()),
        "page": page,
        "limit": limit,
    }


async def query_sec_insiders(
    db: AsyncSession,
    *,
    q: str | None = None,
    page: int = 1,
    limit: int = 50,
) -> dict[str, Any]:
    page = max(1, page)
    limit = min(100, max(1, limit))
    offset = (page - 1) * limit
    query_text = (q or "").strip()

    if query_text:
        count_row = await db.execute(
            text("""
                SELECT COUNT(*) FROM sec_insiders
                WHERE search_vector @@ plainto_tsquery('english', :q)
            """),
            {"q": query_text},
        )
        rows = await db.execute(
            text("""
                SELECT id, reporting_owner_cik, name, company_name, company_cik, ticker,
                       form_type, filed_at, transaction_date, action, amount, shares,
                       avg_price, accession_number
                FROM sec_insiders
                WHERE search_vector @@ plainto_tsquery('english', :q)
                ORDER BY filed_at DESC LIMIT :limit OFFSET :offset
            """),
            {"q": query_text, "limit": limit, "offset": offset},
        )
    else:
        count_row = await db.execute(text("SELECT COUNT(*) FROM sec_insiders"))
        rows = await db.execute(
            text("""
                SELECT id, reporting_owner_cik, name, company_name, company_cik, ticker,
                       form_type, filed_at, transaction_date, action, amount, shares,
                       avg_price, accession_number
                FROM sec_insiders
                ORDER BY filed_at DESC LIMIT :limit OFFSET :offset
            """),
            {"limit": limit, "offset": offset},
        )

    insiders = []
    for r in rows:
        insiders.append({
            "id": r.id,
            "reportingOwnerCik": strip_cik(r.reporting_owner_cik) if r.reporting_owner_cik else None,
            "name": r.name,
            "companyName": r.company_name,
            "companyCik": r.company_cik,
            "ticker": r.ticker,
            "formType": r.form_type,
            "filedAt": r.filed_at.isoformat() if r.filed_at else "",
            "transactionDate": str(r.transaction_date) if r.transaction_date else None,
            "action": r.action,
            "amount": int(r.amount) if r.amount is not None else None,
            "shares": int(r.shares) if r.shares is not None else None,
            "avgPrice": float(r.avg_price) if r.avg_price is not None else None,
            "accessionNumber": r.accession_number,
        })

    return {
        "insiders": insiders,
        "total": int(count_row.scalar_one()),
        "page": page,
        "limit": limit,
    }


async def query_filer_cik_by_name(db: AsyncSession, name: str) -> str | None:
    exact = await db.execute(
        text("""
            SELECT cik FROM sec_filers WHERE name ILIKE :name
            ORDER BY total_portfolio_value DESC LIMIT 1
        """),
        {"name": name},
    )
    row = exact.first()
    if row:
        return strip_cik(row.cik)
    fuzzy = await db.execute(
        text("""
            SELECT cik FROM sec_filers
            WHERE search_vector @@ plainto_tsquery('english', :q)
            ORDER BY total_portfolio_value DESC LIMIT 1
        """),
        {"q": " ".join(name.split()[:3])},
    )
    fuzzy_row = fuzzy.first()
    return strip_cik(fuzzy_row.cik) if fuzzy_row else None


def get_mock_investments(action: str | None = None, sector: str | None = None) -> list[dict[str, Any]]:
    items = list(MOCK_INVESTMENTS)
    if action and action != "all":
        items = [i for i in items if i.get("action") == action]
    if sector and sector != "all":
        items = [i for i in items if i.get("sector") == sector]
    return items
