import re
import statistics
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import create_engine, desc, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from backend.config import settings
from backend.models.announcement import Announcement
from backend.models.computed_ratio import ComputedRatio
from backend.models.financial import FinancialLineItem, FinancialPeriod
from backend.models.price import Price
from backend.models.scraper_run import ScraperRun
from backend.models.ticker import Ticker

RATIO_CODES = [
    "pe_ttm",
    "eps_ttm",
    "dividend_yield",
    "gross_margin",
    "ebitda_margin",
    "net_margin",
    "roe",
    "roa",
    "debt_to_equity",
    "current_ratio",
]


def get_sync_session() -> Session:
    engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
    return sessionmaker(bind=engine)()


def record_scraper_run(
    session: Session,
    scraper_name: str,
    *,
    success: bool,
    records: int = 0,
    error: str | None = None,
) -> None:
    now = datetime.now(UTC)
    session.add(
        ScraperRun(
            scraper_name=scraper_name,
            last_success_at=now if success else None,
            last_run_at=now,
            records_ingested=records,
            error_message=error,
        )
    )


def _line_value(session: Session, symbol: str, code: str, period_type: str = "quarterly") -> Decimal | None:
    result = session.execute(
        select(FinancialLineItem.value)
        .join(FinancialPeriod, FinancialPeriod.id == FinancialLineItem.period_id)
        .where(
            FinancialPeriod.symbol == symbol,
            FinancialPeriod.period_type == period_type,
            FinancialLineItem.line_code == code,
        )
        .order_by(desc(FinancialPeriod.period_end))
        .limit(1)
    )
    val = result.scalar_one_or_none()
    return Decimal(str(val)) if val is not None else None


def _line_ttm(session: Session, symbol: str, code: str) -> Decimal | None:
    rows = session.execute(
        select(FinancialLineItem.value)
        .join(FinancialPeriod, FinancialPeriod.id == FinancialLineItem.period_id)
        .where(
            FinancialPeriod.symbol == symbol,
            FinancialPeriod.period_type == "quarterly",
            FinancialLineItem.line_code == code,
        )
        .order_by(desc(FinancialPeriod.period_end))
        .limit(4)
    ).scalars().all()
    if not rows:
        return _line_value(session, symbol, code, "annual")
    return sum(Decimal(str(v)) for v in rows)


def _latest_price(session: Session, symbol: str) -> Decimal | None:
    row = session.scalar(
        select(Price.close)
        .where(Price.symbol == symbol)
        .order_by(desc(Price.time))
        .limit(1)
    )
    return Decimal(str(row)) if row is not None else None


def _annual_dividend(session: Session, symbol: str) -> Decimal | None:
    rows = session.scalars(
        select(Announcement.title)
        .where(
            Announcement.symbol == symbol,
            Announcement.category == "dividend",
        )
        .order_by(desc(Announcement.published_at))
        .limit(4)
    ).all()
    total = Decimal("0")
    for title in rows:
        match = re.search(r"rs\.?\s*([\d,.]+)", title.lower())
        if match:
            try:
                total += Decimal(match.group(1).replace(",", ""))
            except Exception:
                continue
    return total if total > 0 else None


def _safe_div(num: Decimal | None, den: Decimal | None) -> Decimal | None:
    if num is None or den is None or den == 0:
        return None
    return num / den


def compute_symbol_ratios(session: Session, symbol: str) -> tuple[dict[str, Decimal | None], datetime | None]:
    revenue = _line_ttm(session, symbol, "revenue")
    gross_profit = _line_ttm(session, symbol, "gross_profit")
    ebitda = _line_ttm(session, symbol, "ebitda")
    pat = _line_ttm(session, symbol, "pat")
    eps_ttm = _line_ttm(session, symbol, "eps_basic")
    total_assets = _line_value(session, symbol, "total_assets")
    total_equity = _line_value(session, symbol, "total_equity")
    total_debt = _line_value(session, symbol, "total_debt")
    current_assets = _line_value(session, symbol, "current_assets")
    current_liabilities = _line_value(session, symbol, "current_liabilities")
    price = _latest_price(session, symbol)
    annual_div = _annual_dividend(session, symbol)

    period_end = session.scalar(
        select(FinancialPeriod.period_end)
        .where(FinancialPeriod.symbol == symbol)
        .order_by(desc(FinancialPeriod.period_end))
        .limit(1)
    )

    ratios: dict[str, Decimal | None] = {
        "eps_ttm": eps_ttm,
        "pe_ttm": _safe_div(price, eps_ttm) if price and eps_ttm else None,
        "dividend_yield": _safe_div(annual_div, price) * 100 if annual_div and price else None,
        "gross_margin": _safe_div(gross_profit, revenue) * 100 if gross_profit and revenue else None,
        "ebitda_margin": _safe_div(ebitda, revenue) * 100 if ebitda and revenue else None,
        "net_margin": _safe_div(pat, revenue) * 100 if pat and revenue else None,
        "roe": _safe_div(pat, total_equity) * 100 if pat and total_equity else None,
        "roa": _safe_div(pat, total_assets) * 100 if pat and total_assets else None,
        "debt_to_equity": _safe_div(total_debt, total_equity) if total_debt and total_equity else None,
        "current_ratio": _safe_div(current_assets, current_liabilities)
        if current_assets and current_liabilities
        else None,
    }
    return ratios, period_end


def upsert_symbol_ratios(session: Session, symbol: str) -> int:
    ratios, period_end = compute_symbol_ratios(session, symbol)
    if not period_end:
        return 0
    count = 0
    for code, value in ratios.items():
        if value is None:
            continue
        stmt = insert(ComputedRatio).values(
            symbol=symbol,
            period_end=period_end,
            ratio_code=code,
            value=value,
            computed_at=datetime.now(UTC),
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_computed_ratios",
            set_={"value": stmt.excluded.value, "computed_at": stmt.excluded.computed_at},
        )
        session.execute(stmt)
        count += 1
    return count


def batch_upsert_symbol_ratios(symbols: list[str]) -> dict:
    if not symbols:
        return {"ratios_upserted": 0, "symbols": 0}
    session = get_sync_session()
    try:
        total = 0
        for symbol in symbols:
            try:
                total += upsert_symbol_ratios(session, symbol)
            except Exception:
                continue
        session.commit()
        return {"ratios_upserted": total, "symbols": len(symbols)}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def recompute_all_ratios() -> dict:
    session = get_sync_session()
    try:
        symbols = list(
            session.scalars(
                select(Ticker.symbol).where(Ticker.is_active.is_(True), Ticker.is_debt.is_(False))
            )
        )
        total = 0
        for symbol in symbols:
            try:
                total += upsert_symbol_ratios(session, symbol)
            except Exception:
                continue
        record_scraper_run(session, "recompute_ratios", success=True, records=total)
        session.commit()
        from backend.services.cache import flush_cache_pattern_sync

        cache_cleared = flush_cache_pattern_sync("screener:*")
        return {"ratios_upserted": total, "symbols": len(symbols), "screener_cache_cleared": cache_cleared}
    except Exception as exc:
        session.rollback()
        record_scraper_run(session, "recompute_ratios", success=False, error=str(exc))
        session.commit()
        raise
    finally:
        session.close()


def sector_medians(session: Session, sector: str) -> dict[str, float]:
    tickers = list(
        session.scalars(select(Ticker.symbol).where(Ticker.sector == sector, Ticker.is_active.is_(True)))
    )
    if not tickers:
        return {}
    medians: dict[str, list[float]] = {code: [] for code in RATIO_CODES}
    for sym in tickers:
        ratios, _ = compute_symbol_ratios(session, sym)
        for code, val in ratios.items():
            if val is not None:
                medians[code].append(float(val))
    return {
        code: float(statistics.median(values))
        for code, values in medians.items()
        if values
    }


def run_recompute_ratios() -> dict:
    return recompute_all_ratios()
