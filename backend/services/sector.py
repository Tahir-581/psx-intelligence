"""Sector daily statistics aggregation."""

from __future__ import annotations

import json
import statistics
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from fastapi import HTTPException
from redis.asyncio import Redis
from sqlalchemy import and_, create_engine, desc, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, sessionmaker

from backend.config import settings
from backend.models.computed_ratio import ComputedRatio
from backend.models.financial import FinancialLineItem, FinancialPeriod
from backend.models.price import Price
from backend.models.scraper_run import ScraperRun
from backend.models.sector_daily_stats import SectorDailyStats
from backend.models.ticker import Ticker
from backend.schemas.context import (
    SectorCompanyFinancials,
    SectorCompanyRow,
    SectorDetailResponse,
    SectorStatsItem,
    SectorStatsResponse,
)
from backend.services.screener import (
    _fetch_betas_for_symbols,
    _latest_price_subquery,
    _latest_ratio_subquery,
    _price_stats_subquery,
)

STATEMENT_LINE_CODES = (
    "revenue",
    "gross_profit",
    "ebitda",
    "pat",
    "total_assets",
    "total_equity",
    "total_debt",
    "ocf",
    "capex",
)

RATIO_CODES_FOR_DETAIL = (
    "pe_ttm",
    "eps_ttm",
    "dividend_yield",
    "roe",
    "roa",
    "gross_margin",
    "ebitda_margin",
    "net_margin",
    "debt_to_equity",
    "current_ratio",
)


def get_sync_session() -> Session:
    engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
    return sessionmaker(bind=engine)()


RANGE_FIELD = {
    "1d": "return_1d",
    "1w": "return_1w",
    "1m": "return_1m",
    "ytd": "return_ytd",
}


def _return_range_subquery(range_key: str):
    if range_key == "ytd":
        cutoff = datetime(date.today().year, 1, 1, tzinfo=UTC)
    else:
        days_map = {"1d": 1, "1w": 7, "1m": 30}
        cutoff = datetime.now(UTC) - timedelta(days=days_map.get(range_key, 1))

    latest = _latest_price_subquery()
    past = (
        select(
            Price.symbol,
            Price.close.label("past_close"),
            func.row_number()
            .over(partition_by=Price.symbol, order_by=desc(Price.time))
            .label("rn"),
        )
        .where(Price.time <= cutoff)
        .subquery()
    )
    past_price = select(past.c.symbol, past.c.past_close).where(past.c.rn == 1).subquery()
    return (
        select(
            latest.c.symbol,
            (
                (latest.c.ltp - past_price.c.past_close)
                / func.nullif(past_price.c.past_close, 0)
                * 100
            ).label("return_range"),
        )
        .outerjoin(past_price, latest.c.symbol == past_price.c.symbol)
        .subquery()
    )


async def _fetch_latest_financials_batch(
    db: AsyncSession,
    symbols: list[str],
) -> dict[str, dict]:
    if not symbols:
        return {}

    ranked = (
        select(
            FinancialPeriod.id,
            FinancialPeriod.symbol,
            FinancialPeriod.period_end,
            func.row_number()
            .over(
                partition_by=FinancialPeriod.symbol,
                order_by=desc(FinancialPeriod.period_end),
            )
            .label("rn"),
        )
        .where(FinancialPeriod.symbol.in_(symbols))
        .subquery()
    )
    latest = select(ranked).where(ranked.c.rn == 1).subquery()

    result = await db.execute(
        select(
            latest.c.symbol,
            latest.c.period_end,
            FinancialLineItem.line_code,
            FinancialLineItem.value,
        )
        .join(FinancialLineItem, FinancialLineItem.period_id == latest.c.id)
        .where(FinancialLineItem.line_code.in_(STATEMENT_LINE_CODES))
    )

    out: dict[str, dict] = {}
    for row in result.all():
        if row.symbol not in out:
            out[row.symbol] = {"period_end": row.period_end}
        out[row.symbol][row.line_code] = float(row.value)
    return out


async def _get_sector_stats_item(
    db: AsyncSession,
    sector: str,
) -> tuple[date | None, SectorStatsItem | None]:
    latest_date = await db.scalar(select(func.max(SectorDailyStats.trade_date)))
    if not latest_date:
        return None, None
    row = await db.scalar(
        select(SectorDailyStats).where(
            SectorDailyStats.trade_date == latest_date,
            SectorDailyStats.sector == sector,
        )
    )
    if not row:
        return latest_date, None
    return latest_date, SectorStatsItem(
        sector=row.sector,
        company_count=row.company_count,
        total_market_cap=float(row.total_market_cap) if row.total_market_cap else None,
        median_pe=float(row.median_pe) if row.median_pe else None,
        median_dividend_yield=float(row.median_dividend_yield)
        if row.median_dividend_yield
        else None,
        return_1d=float(row.return_1d) if row.return_1d else None,
        return_1w=float(row.return_1w) if row.return_1w else None,
        return_1m=float(row.return_1m) if row.return_1m else None,
        return_ytd=float(row.return_ytd) if row.return_ytd else None,
        top_gainer_symbol=row.top_gainer_symbol,
        top_loser_symbol=row.top_loser_symbol,
    )


async def get_sector_detail(
    db: AsyncSession,
    redis: Redis,
    sector: str,
    *,
    range_key: str = "1d",
) -> SectorDetailResponse:
    trade_date, stats = await _get_sector_stats_item(db, sector)

    price_sq = _latest_price_subquery()
    stats_sq = _price_stats_subquery()
    return_sq = _return_range_subquery(range_key)

    ratio_sqs = {code: _latest_ratio_subquery(code) for code in RATIO_CODES_FOR_DETAIL}

    market_cap_expr = (price_sq.c.ltp * Ticker.shares_outstanding).label("market_cap")

    query = (
        select(
            Ticker.symbol,
            Ticker.name,
            price_sq.c.ltp,
            price_sq.c.latest_volume,
            market_cap_expr,
            stats_sq.c.avg_volume_30d,
            return_sq.c.return_range,
            *[ratio_sqs[code].c[code] for code in RATIO_CODES_FOR_DETAIL],
        )
        .select_from(Ticker)
        .outerjoin(price_sq, Ticker.symbol == price_sq.c.symbol)
        .outerjoin(stats_sq, Ticker.symbol == stats_sq.c.symbol)
        .outerjoin(return_sq, Ticker.symbol == return_sq.c.symbol)
    )
    for code in RATIO_CODES_FOR_DETAIL:
        query = query.outerjoin(ratio_sqs[code], Ticker.symbol == ratio_sqs[code].c.symbol)

    query = query.where(
        Ticker.is_active.is_(True),
        Ticker.is_debt.is_(False),
        Ticker.sector == sector,
    ).order_by(desc(market_cap_expr))

    result = await db.execute(query)
    rows = result.all()
    if not rows and stats is None:
        raise HTTPException(status_code=404, detail=f"Sector '{sector}' not found.")

    symbols = [row.symbol for row in rows]
    beta_map = await _fetch_betas_for_symbols(db, redis, symbols)
    financials_map = await _fetch_latest_financials_batch(db, symbols)

    companies: list[SectorCompanyRow] = []
    for row in rows:
        ltp = float(row.ltp) if row.ltp is not None else None
        change_pct = None
        cached_snap = await redis.get(f"ticker:{row.symbol}:snapshot")
        if cached_snap:
            data = json.loads(cached_snap)
            ltp = float(data.get("ltp", ltp or 0)) or ltp
            change_pct = data.get("change_pct")

        fin_raw = financials_map.get(row.symbol, {})
        financials = SectorCompanyFinancials(
            revenue=fin_raw.get("revenue"),
            gross_profit=fin_raw.get("gross_profit"),
            ebitda=fin_raw.get("ebitda"),
            pat=fin_raw.get("pat"),
            total_assets=fin_raw.get("total_assets"),
            total_equity=fin_raw.get("total_equity"),
            total_debt=fin_raw.get("total_debt"),
            ocf=fin_raw.get("ocf"),
            capex=fin_raw.get("capex"),
            period_end=fin_raw.get("period_end"),
        )

        companies.append(
            SectorCompanyRow(
                symbol=row.symbol,
                name=row.name,
                ltp=ltp,
                change_pct=float(change_pct) if change_pct is not None else None,
                market_cap=float(row.market_cap) if row.market_cap is not None else None,
                volume=int(row.latest_volume) if row.latest_volume is not None else None,
                avg_volume_30d=float(row.avg_volume_30d)
                if row.avg_volume_30d is not None
                else None,
                pe_ttm=float(row.pe_ttm) if row.pe_ttm is not None else None,
                eps_ttm=float(row.eps_ttm) if row.eps_ttm is not None else None,
                dividend_yield=float(row.dividend_yield)
                if row.dividend_yield is not None
                else None,
                roe=float(row.roe) if row.roe is not None else None,
                roa=float(row.roa) if row.roa is not None else None,
                gross_margin=float(row.gross_margin) if row.gross_margin is not None else None,
                ebitda_margin=float(row.ebitda_margin)
                if row.ebitda_margin is not None
                else None,
                net_margin=float(row.net_margin) if row.net_margin is not None else None,
                debt_to_equity=float(row.debt_to_equity)
                if row.debt_to_equity is not None
                else None,
                current_ratio=float(row.current_ratio)
                if row.current_ratio is not None
                else None,
                beta=beta_map.get(row.symbol),
                return_range=float(row.return_range) if row.return_range is not None else None,
                financials=financials,
            )
        )

    return SectorDetailResponse(
        sector=sector,
        range=range_key,
        trade_date=trade_date,
        stats=stats,
        companies=companies,
    )


async def get_sector_stats(
    db: AsyncSession,
    *,
    range_key: str = "1d",
) -> SectorStatsResponse:
    latest_date = await db.scalar(select(func.max(SectorDailyStats.trade_date)))
    if not latest_date:
        return SectorStatsResponse(trade_date=None, range=range_key, sectors=[])
    result = await db.execute(
        select(SectorDailyStats).where(SectorDailyStats.trade_date == latest_date)
    )
    sectors = []
    for row in result.scalars().all():
        ret = getattr(row, RANGE_FIELD.get(range_key, "return_1d"), None)
        sectors.append(
            SectorStatsItem(
                sector=row.sector,
                company_count=row.company_count,
                total_market_cap=float(row.total_market_cap) if row.total_market_cap else None,
                median_pe=float(row.median_pe) if row.median_pe else None,
                median_dividend_yield=float(row.median_dividend_yield)
                if row.median_dividend_yield
                else None,
                return_1d=float(row.return_1d) if row.return_1d else None,
                return_1w=float(row.return_1w) if row.return_1w else None,
                return_1m=float(row.return_1m) if row.return_1m else None,
                return_ytd=float(row.return_ytd) if row.return_ytd else None,
                top_gainer_symbol=row.top_gainer_symbol,
                top_loser_symbol=row.top_loser_symbol,
            )
        )
    # Sort by selected return descending
    field = RANGE_FIELD.get(range_key, "return_1d")
    sectors.sort(key=lambda s: getattr(s, field) or 0, reverse=True)
    return SectorStatsResponse(trade_date=latest_date, range=range_key, sectors=sectors)


def _period_return(closes: list[tuple[date, float]], days: int) -> float | None:
    if len(closes) < 2:
        return None
    end_price = closes[-1][1]
    cutoff = closes[-1][0] - timedelta(days=days)
    start_price = None
    for d, p in closes:
        if d <= cutoff:
            start_price = p
    if start_price is None:
        start_price = closes[0][1]
    if not start_price:
        return None
    return ((end_price - start_price) / start_price) * 100


def run_refresh_sector_stats() -> dict:
    session = get_sync_session()
    try:
        tickers = session.scalars(
            select(Ticker).where(Ticker.is_active.is_(True), Ticker.is_debt.is_(False))
        ).all()
        sectors: dict[str, list[Ticker]] = {}
        for t in tickers:
            sectors.setdefault(t.sector, []).append(t)

        trade_date = date.today()
        rows: list[dict] = []
        for sector, sector_tickers in sectors.items():
            market_caps: list[float] = []
            pes: list[float] = []
            div_yields: list[float] = []
            returns_1d: list[tuple[str, float]] = []

            for ticker in sector_tickers:
                latest_price = session.scalar(
                    select(Price)
                    .where(Price.symbol == ticker.symbol)
                    .order_by(desc(Price.time))
                    .limit(1)
                )
                if not latest_price:
                    continue
                ltp = float(latest_price.close)
                if ticker.shares_outstanding:
                    market_caps.append(ltp * ticker.shares_outstanding)

                ratio_pe = session.scalar(
                    select(ComputedRatio.value)
                    .where(
                        ComputedRatio.symbol == ticker.symbol,
                        ComputedRatio.ratio_code == "pe_ttm",
                    )
                    .order_by(desc(ComputedRatio.period_end))
                    .limit(1)
                )
                if ratio_pe:
                    pes.append(float(ratio_pe))
                ratio_div = session.scalar(
                    select(ComputedRatio.value)
                    .where(
                        ComputedRatio.symbol == ticker.symbol,
                        ComputedRatio.ratio_code == "dividend_yield",
                    )
                    .order_by(desc(ComputedRatio.period_end))
                    .limit(1)
                )
                if ratio_div:
                    div_yields.append(float(ratio_div))

                year_start = date(trade_date.year, 1, 1)
                prices = session.execute(
                    select(Price.time, Price.close)
                    .where(Price.symbol == ticker.symbol)
                    .order_by(Price.time.asc())
                ).all()
                closes = [(p.time.date(), float(p.close)) for p in prices]
                ret_1d = _period_return(closes, 1)
                if ret_1d is not None:
                    returns_1d.append((ticker.symbol, ret_1d))

            top_gainer = max(returns_1d, key=lambda x: x[1])[0] if returns_1d else None
            top_loser = min(returns_1d, key=lambda x: x[1])[0] if returns_1d else None

            ret_1d_val = ret_1w = ret_1m = ret_ytd = None
            sample = sector_tickers[0] if sector_tickers else None
            if sample:
                prices = session.execute(
                    select(Price.time, Price.close)
                    .where(Price.symbol == sample.symbol)
                    .order_by(Price.time.asc())
                ).all()
                closes = [(p.time.date(), float(p.close)) for p in prices]
                ret_1d_val = _period_return(closes, 1)
                ret_1w = _period_return(closes, 7)
                ret_1m = _period_return(closes, 30)
                ret_ytd = _period_return(closes, (trade_date - date(trade_date.year, 1, 1)).days)

            rows.append(
                {
                    "trade_date": trade_date,
                    "sector": sector,
                    "company_count": len(sector_tickers),
                    "total_market_cap": Decimal(str(sum(market_caps))) if market_caps else None,
                    "median_pe": Decimal(str(statistics.median(pes))) if pes else None,
                    "median_dividend_yield": Decimal(str(statistics.median(div_yields)))
                    if div_yields
                    else None,
                    "return_1d": Decimal(str(ret_1d_val)) if sample and ret_1d_val else None,
                    "return_1w": Decimal(str(ret_1w)) if ret_1w else None,
                    "return_1m": Decimal(str(ret_1m)) if ret_1m else None,
                    "return_ytd": Decimal(str(ret_ytd)) if ret_ytd else None,
                    "top_gainer_symbol": top_gainer,
                    "top_loser_symbol": top_loser,
                }
            )

        if rows:
            stmt = insert(SectorDailyStats).values(rows)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_sector_daily_stats",
                set_={
                    "company_count": stmt.excluded.company_count,
                    "total_market_cap": stmt.excluded.total_market_cap,
                    "median_pe": stmt.excluded.median_pe,
                    "median_dividend_yield": stmt.excluded.median_dividend_yield,
                    "return_1d": stmt.excluded.return_1d,
                    "return_1w": stmt.excluded.return_1w,
                    "return_1m": stmt.excluded.return_1m,
                    "return_ytd": stmt.excluded.return_ytd,
                    "top_gainer_symbol": stmt.excluded.top_gainer_symbol,
                    "top_loser_symbol": stmt.excluded.top_loser_symbol,
                },
            )
            session.execute(stmt)
            session.commit()

        session.add(
            ScraperRun(
                scraper_name="refresh_sector_stats",
                last_success_at=datetime.now(UTC),
                last_run_at=datetime.now(UTC),
                records_ingested=len(rows),
            )
        )
        session.commit()
        return {"sectors": len(rows)}
    except Exception as exc:
        session.rollback()
        session.add(
            ScraperRun(
                scraper_name="refresh_sector_stats",
                last_run_at=datetime.now(UTC),
                error_message=str(exc)[:500],
            )
        )
        session.commit()
        raise
    finally:
        session.close()
