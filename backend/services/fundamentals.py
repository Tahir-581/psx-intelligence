from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.announcement import Announcement
from backend.models.computed_ratio import ComputedRatio
from backend.models.financial import FinancialLineItem, FinancialPeriod
from backend.models.insider_trade import InsiderTrade
from backend.models.ownership import OwnershipSnapshot
from backend.models.ticker import Ticker
from backend.schemas.fundamentals import (
    AnnouncementItem,
    AnnouncementListResponse,
    FinancialLineRow,
    FinancialPeriodColumn,
    FinancialsResponse,
    InsiderTradeItem,
    InsiderTradesResponse,
    OwnershipHistoryPoint,
    OwnershipResponse,
    OwnershipSnapshotItem,
    RatioHistoryPoint,
    RatioValue,
    RatiosResponse,
)
from backend.services.financial_validation import compute_yoy_changes, validate_financials
from backend.services.ratios import RATIO_CODES


async def get_announcements(
    db: AsyncSession,
    symbol: str,
    *,
    category: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> AnnouncementListResponse:
    query = select(Announcement).where(Announcement.symbol == symbol)
    if category:
        query = query.where(Announcement.category == category)
    count_q = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_q) or 0
    result = await db.execute(
        query.order_by(desc(Announcement.published_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [
        AnnouncementItem(
            id=row.id,
            symbol=row.symbol,
            published_at=row.published_at,
            title=row.title,
            category=row.category,
            pdf_url=row.pdf_url,
            source_url=row.source_url,
            body_text=row.body_text,
        )
        for row in result.scalars().all()
    ]
    return AnnouncementListResponse(
        items=items, total=total, page=page, page_size=page_size
    )


async def get_financials(
    db: AsyncSession, symbol: str, *, period_type: str = "quarterly", max_periods: int | None = None
) -> FinancialsResponse:
    limit = max_periods if max_periods is not None else 12
    periods_result = await db.execute(
        select(FinancialPeriod)
        .where(FinancialPeriod.symbol == symbol, FinancialPeriod.period_type == period_type)
        .order_by(desc(FinancialPeriod.period_end))
        .limit(limit)
    )
    periods = list(periods_result.scalars().all())
    if not periods:
        return FinancialsResponse(symbol=symbol, period_type=period_type, periods=[], rows=[])

    period_cols = [
        FinancialPeriodColumn(
            period_id=p.id,
            period_end=p.period_end,
            fiscal_year=p.fiscal_year,
            fiscal_quarter=p.fiscal_quarter,
            parser_confidence=float(p.parser_confidence) if p.parser_confidence else None,
            is_verified=p.is_verified,
            source_pdf_url=p.source_pdf_url,
        )
        for p in reversed(periods)
    ]
    period_ids = [p.id for p in periods]
    items_result = await db.execute(
        select(FinancialLineItem)
        .where(FinancialLineItem.period_id.in_(period_ids))
        .order_by(FinancialLineItem.line_code)
    )
    line_items = items_result.scalars().all()
    by_code: dict[str, dict[int, tuple[float, str]]] = {}
    for item in line_items:
        by_code.setdefault(item.line_code, {})[item.period_id] = (
            float(item.value),
            item.unit,
        )

    rows = []
    yoy_map = compute_yoy_changes(period_cols, by_code)
    for code in sorted(by_code.keys()):
        values = {}
        unit = "absolute"
        for col in period_cols:
            if col.period_id in by_code[code]:
                val, unit = by_code[code][col.period_id]
                values[col.period_end.isoformat()] = val
        rows.append(
            FinancialLineRow(
                line_code=code,
                unit=unit,
                values=values,
                yoy_change_pct=yoy_map.get(code, {}),
            )
        )

    validation_flags = validate_financials(by_code, period_ids)

    low_confidence = any(
        p.parser_confidence is not None and float(p.parser_confidence) < 0.8 for p in periods
    )
    return FinancialsResponse(
        symbol=symbol,
        period_type=period_type,
        periods=period_cols,
        rows=rows,
        low_confidence=low_confidence,
        validation_flags=validation_flags,
    )


async def get_ratios(db: AsyncSession, symbol: str) -> RatiosResponse:
    ticker = await db.get(Ticker, symbol)
    sector = ticker.sector if ticker else "Unknown"

    latest_result = await db.execute(
        select(ComputedRatio)
        .where(ComputedRatio.symbol == symbol)
        .order_by(desc(ComputedRatio.period_end), ComputedRatio.ratio_code)
    )
    all_rows = latest_result.scalars().all()
    latest_period = all_rows[0].period_end if all_rows else None
    latest_map: dict[str, float | None] = {}
    if latest_period:
        for row in all_rows:
            if row.period_end == latest_period:
                latest_map[row.ratio_code] = float(row.value) if row.value is not None else None

    history: list[RatioHistoryPoint] = []
    seen_periods: set[date] = set()
    for row in all_rows:
        if row.period_end in seen_periods:
            continue
        seen_periods.add(row.period_end)
        period_rows = [r for r in all_rows if r.period_end == row.period_end]
        history.append(
            RatioHistoryPoint(
                period_end=row.period_end,
                ratios={
                    r.ratio_code: float(r.value) if r.value is not None else None
                    for r in period_rows
                },
            )
        )

    latest = [RatioValue(code=c, value=latest_map.get(c)) for c in RATIO_CODES if c in latest_map]
    medians = sector_medians_sync_placeholder(db, sector)
    return RatiosResponse(
        symbol=symbol,
        sector=sector,
        latest=latest,
        history=history[:20],
        sector_medians=medians,
    )


async def sector_medians_sync_placeholder(db: AsyncSession, sector: str) -> dict[str, float]:
    """Compute sector medians using latest stored ratios per ticker."""
    tickers_result = await db.execute(
        select(Ticker.symbol).where(Ticker.sector == sector, Ticker.is_active.is_(True))
    )
    symbols = list(tickers_result.scalars().all())
    if not symbols:
        return {}
    values_by_code: dict[str, list[float]] = {c: [] for c in RATIO_CODES}
    for sym in symbols:
        result = await db.execute(
            select(ComputedRatio)
            .where(ComputedRatio.symbol == sym)
            .order_by(desc(ComputedRatio.period_end))
        )
        rows = result.scalars().all()
        if not rows:
            continue
        latest_pe = rows[0].period_end
        for row in rows:
            if row.period_end != latest_pe:
                break
            if row.value is not None:
                values_by_code.setdefault(row.ratio_code, []).append(float(row.value))
    import statistics

    return {
        code: float(statistics.median(vals))
        for code, vals in values_by_code.items()
        if vals
    }


async def get_insider_trades(
    db: AsyncSession, symbol: str, *, days: int = 90
) -> InsiderTradesResponse:
    cutoff = datetime.now(UTC).date() - timedelta(days=days)
    result = await db.execute(
        select(InsiderTrade)
        .where(InsiderTrade.symbol == symbol, InsiderTrade.transaction_date >= cutoff)
        .order_by(desc(InsiderTrade.transaction_date))
    )
    trades = [
        InsiderTradeItem(
            id=row.id,
            director_name=row.director_name,
            designation=row.designation,
            transaction_date=row.transaction_date,
            transaction_type=row.transaction_type,
            shares=row.shares,
            price_per_share=float(row.price_per_share) if row.price_per_share else None,
            post_holding_shares=row.post_holding_shares,
        )
        for row in result.scalars().all()
    ]

    def net_for(days_back: int) -> int:
        since = datetime.now(UTC).date() - timedelta(days=days_back)
        total = 0
        for t in trades:
            if t.transaction_date < since:
                continue
            sign = 1 if t.transaction_type in ("buy", "unpledge") else -1
            total += sign * t.shares
        return total

    return InsiderTradesResponse(
        symbol=symbol,
        trades=trades,
        net_30d=net_for(30),
        net_90d=net_for(90),
        cluster_buy_14d=_cluster_buy_14d(trades),
    )


def _cluster_buy_14d(trades: list[InsiderTradeItem]) -> bool:
    cutoff = datetime.now(UTC).date() - timedelta(days=14)
    buyers: set[str] = set()
    for t in trades:
        if t.transaction_date >= cutoff and t.transaction_type == "buy":
            buyers.add(t.director_name)
    return len(buyers) >= 2


async def get_ownership(db: AsyncSession, symbol: str) -> OwnershipResponse:
    result = await db.execute(
        select(OwnershipSnapshot)
        .where(OwnershipSnapshot.symbol == symbol)
        .order_by(desc(OwnershipSnapshot.as_of_date))
    )
    rows = result.scalars().all()
    if not rows:
        return OwnershipResponse(
            symbol=symbol,
            latest_snapshot=[],
            history=[],
            pledged_shares_pct=None,
            pledged_warning=False,
            named_holders=[],
            free_float_pct=None,
        )

    latest_date = rows[0].as_of_date
    latest = [
        OwnershipSnapshotItem(
            holder_category=r.holder_category,
            shares=r.shares,
            pct_outstanding=float(r.pct_outstanding),
            pledged_shares_pct=float(r.pledged_shares_pct) if r.pledged_shares_pct else None,
            holder_name=r.holder_name,
        )
        for r in rows
        if r.as_of_date == latest_date
    ]

    pledged_pct = None
    for r in rows:
        if r.as_of_date == latest_date and r.pledged_shares_pct is not None:
            pledged_pct = float(r.pledged_shares_pct)
            break

    named_holders = [
        item for item in latest
        if item.holder_name and item.pct_outstanding >= 5.0
    ]

    by_date: dict[date, list[OwnershipSnapshotItem]] = {}
    for r in rows:
        by_date.setdefault(r.as_of_date, []).append(
            OwnershipSnapshotItem(
                holder_category=r.holder_category,
                shares=r.shares,
                pct_outstanding=float(r.pct_outstanding),
                pledged_shares_pct=float(r.pledged_shares_pct) if r.pledged_shares_pct else None,
                holder_name=r.holder_name,
            )
        )
    history = [
        OwnershipHistoryPoint(as_of_date=d, snapshots=snapshots)
        for d, snapshots in sorted(by_date.items())
    ][:8]
    free_float = await get_free_float_pct(db, symbol)
    sponsor = next((i for i in latest if i.holder_category in ("sponsor", "sponsors")), None)
    pledged_warning = bool(
        pledged_pct is not None and sponsor and pledged_pct > 20.0
    )
    return OwnershipResponse(
        symbol=symbol,
        latest_snapshot=latest,
        history=history,
        pledged_shares_pct=pledged_pct,
        pledged_warning=pledged_warning,
        named_holders=named_holders,
        free_float_pct=free_float,
    )


async def get_free_float_pct(db: AsyncSession, symbol: str) -> float | None:
    result = await db.execute(
        select(OwnershipSnapshot)
        .where(OwnershipSnapshot.symbol == symbol)
        .order_by(desc(OwnershipSnapshot.as_of_date))
        .limit(20)
    )
    rows = result.scalars().all()
    if not rows:
        return None
    latest_date = rows[0].as_of_date
    public_pct = None
    for r in rows:
        if r.as_of_date != latest_date:
            break
        if r.holder_category in ("public", "general_public"):
            public_pct = float(r.pct_outstanding)
            break
    return public_pct


async def get_latest_ratio_map(db: AsyncSession, symbol: str) -> dict[str, float]:
    result = await db.execute(
        select(ComputedRatio)
        .where(ComputedRatio.symbol == symbol)
        .order_by(desc(ComputedRatio.period_end))
    )
    rows = result.scalars().all()
    if not rows:
        return {}
    latest_pe = rows[0].period_end
    out: dict[str, float] = {}
    for row in rows:
        if row.period_end != latest_pe:
            break
        if row.value is not None:
            out[row.ratio_code] = float(row.value)
    return out
