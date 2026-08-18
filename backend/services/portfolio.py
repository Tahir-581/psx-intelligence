"""Portfolio holdings and P&L."""

from __future__ import annotations

import io
import json
from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi import HTTPException
from redis.asyncio import Redis
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.corporate_action import CorporateAction
from backend.models.portfolio_holding import PortfolioHolding
from backend.models.portfolio_transaction import PortfolioTransaction
from backend.models.price import Price
from backend.models.ticker import Ticker
from backend.models.user import User
from backend.schemas.portfolio import (
    HoldingCreate,
    HoldingItem,
    HoldingUpdate,
    PortfolioResponse,
    PortfolioSeriesPoint,
    PortfolioSummary,
    SectorExposureItem,
    TransactionItem,
    TransactionListResponse,
)
from backend.services.market import get_snapshot
from backend.services.risk import get_beta


async def _ltp_for(db: AsyncSession, redis: Redis, symbol: str) -> float | None:
    snap = await get_snapshot(db, redis, symbol)
    return snap.ltp if snap else None


async def get_portfolio(db: AsyncSession, redis: Redis, user: User) -> PortfolioResponse:
    holdings = (
        await db.execute(
            select(PortfolioHolding)
            .where(PortfolioHolding.user_id == user.id)
            .order_by(PortfolioHolding.symbol, PortfolioHolding.purchase_date)
        )
    ).scalars().all()

    items: list[HoldingItem] = []
    total_value = 0.0
    total_cost = 0.0
    sector_values: dict[str, float] = {}
    beta_weighted = 0.0
    beta_total_weight = 0.0
    ytd_start = date(datetime.now(UTC).year, 1, 1)

    for h in holdings:
        ticker = await db.get(Ticker, h.symbol)
        qty = float(h.quantity)
        cost = qty * float(h.avg_buy_price)
        ltp = await _ltp_for(db, redis, h.symbol)
        cur = qty * ltp if ltp else None
        pnl = (cur - cost) if cur is not None else None
        pnl_pct = (pnl / cost * 100) if pnl is not None and cost else None

        if cur is not None:
            total_value += cur
            sector = ticker.sector if ticker else "Unknown"
            sector_values[sector] = sector_values.get(sector, 0) + cur
        total_cost += cost

        dy = None
        yoc = None
        if ticker and ltp:
            snap = await get_snapshot(db, redis, h.symbol)
            if snap and snap.dividend_yield:
                dy = float(snap.dividend_yield)
                annual_div = ltp * dy / 100
                if float(h.avg_buy_price) > 0:
                    yoc = round(annual_div / float(h.avg_buy_price) * 100, 2)

        items.append(
            HoldingItem(
                id=h.id,
                symbol=h.symbol,
                name=ticker.name if ticker else None,
                sector=ticker.sector if ticker else None,
                quantity=qty,
                avg_buy_price=float(h.avg_buy_price),
                purchase_date=h.purchase_date,
                notes=h.notes,
                ltp=ltp,
                current_value=cur,
                cost_basis=cost,
                unrealized_pnl=pnl,
                unrealized_pnl_pct=pnl_pct,
                weight_pct=None,
                yield_on_cost=yoc,
                dividend_yield=dy,
            )
        )

    for item in items:
        if item.current_value and total_value:
            item.weight_pct = round(item.current_value / total_value * 100, 2)
            try:
                beta_resp = await get_beta(db, redis, item.symbol)
                if beta_resp and beta_resp.beta is not None:
                    w = item.current_value / total_value
                    beta_weighted += beta_resp.beta * w
                    beta_total_weight += w
            except Exception:
                pass

    sector_exposure = [
        SectorExposureItem(
            sector=s,
            weight_pct=round(v / total_value * 100, 2) if total_value else 0,
            concentrated=(v / total_value * 100 > 30) if total_value else False,
        )
        for s, v in sorted(sector_values.items(), key=lambda x: -x[1])
    ]
    concentration = any(s.concentrated for s in sector_exposure)

    dividend_ytd = 0.0
    for h in holdings:
        actions = (
            await db.execute(
                select(CorporateAction).where(
                    CorporateAction.symbol == h.symbol,
                    CorporateAction.action_type == "cash_dividend",
                    CorporateAction.record_date >= ytd_start,
                )
            )
        ).scalars().all()
        for a in actions:
            if a.record_date and a.record_date >= h.purchase_date and a.amount_per_share:
                dividend_ytd += float(h.quantity) * float(a.amount_per_share)

    vs_kse100 = await _portfolio_vs_kse100(db, holdings)

    summary = PortfolioSummary(
        total_value=round(total_value, 2),
        total_cost=round(total_cost, 2),
        unrealized_pnl=round(total_value - total_cost, 2),
        unrealized_pnl_pct=round((total_value - total_cost) / total_cost * 100, 2)
        if total_cost
        else 0,
        dividend_income_ytd=round(dividend_ytd, 2),
        portfolio_beta=round(beta_weighted, 3) if beta_total_weight else None,
        sector_exposure=sector_exposure,
        concentration_warning=concentration,
        vs_kse100=vs_kse100,
    )
    return PortfolioResponse(holdings=items, summary=summary)


async def _portfolio_vs_kse100(
    db: AsyncSession, holdings: list[PortfolioHolding]
) -> list[PortfolioSeriesPoint]:
    if not holdings:
        return []
    earliest = min(h.purchase_date for h in holdings)
    from_dt = datetime.combine(earliest, datetime.min.time(), tzinfo=UTC)

    kse_rows = (
        await db.execute(
            select(Price.time, Price.close)
            .where(Price.symbol == "KSE100", Price.time >= from_dt)
            .order_by(Price.time.asc())
        )
    ).all()
    if not kse_rows:
        return []

    kse_base = float(kse_rows[0][1])
    kse_by_date = {r[0].date(): (float(r[1]) / kse_base) * 100 for r in kse_rows}

    symbol_prices: dict[str, dict[date, float]] = {}
    for h in holdings:
        if h.symbol in symbol_prices:
            continue
        rows = (
            await db.execute(
                select(Price.time, Price.close)
                .where(Price.symbol == h.symbol, Price.time >= from_dt)
                .order_by(Price.time.asc())
            )
        ).all()
        if rows:
            base = float(rows[0][1])
            symbol_prices[h.symbol] = {r[0].date(): (float(r[1]) / base) * 100 for r in rows}

    total_cost = sum(float(h.quantity) * float(h.avg_buy_price) for h in holdings)
    dates = sorted(set(kse_by_date.keys()))
    series: list[PortfolioSeriesPoint] = []
    for d in dates:
        port_val = 0.0
        for h in holdings:
            prices = symbol_prices.get(h.symbol, {})
            day_prices = [p for day, p in prices.items() if day <= d]
            if not day_prices:
                continue
            norm = day_prices[-1]
            cost = float(h.quantity) * float(h.avg_buy_price)
            port_val += (norm / 100) * cost
        if total_cost:
            port_norm = (port_val / total_cost) * 100
        else:
            port_norm = 100.0
        series.append(
            PortfolioSeriesPoint(date=d, portfolio=round(port_norm, 2), kse100=kse_by_date.get(d))
        )
    return series[-90:]


async def add_holding(
    db: AsyncSession, redis: Redis, user: User, body: HoldingCreate
) -> PortfolioResponse:
    sym = body.symbol.upper()
    ticker = await db.get(Ticker, sym)
    if not ticker:
        raise HTTPException(status_code=404, detail="Symbol not found.")
    h = PortfolioHolding(
        user_id=user.id,
        symbol=sym,
        quantity=body.quantity,
        avg_buy_price=body.avg_buy_price,
        purchase_date=body.purchase_date,
        notes=body.notes,
    )
    db.add(h)
    db.add(
        PortfolioTransaction(
            user_id=user.id,
            symbol=sym,
            txn_type="buy",
            quantity=body.quantity,
            price=body.avg_buy_price,
            txn_date=body.purchase_date,
        )
    )
    await db.commit()
    return await get_portfolio(db, redis, user)


async def update_holding(
    db: AsyncSession,
    redis: Redis,
    user: User,
    holding_id: int,
    body: HoldingUpdate,
) -> PortfolioResponse:
    h = await db.scalar(
        select(PortfolioHolding).where(
            PortfolioHolding.id == holding_id, PortfolioHolding.user_id == user.id
        )
    )
    if not h:
        raise HTTPException(status_code=404, detail="Holding not found.")
    if body.quantity is not None:
        h.quantity = body.quantity
    if body.avg_buy_price is not None:
        h.avg_buy_price = body.avg_buy_price
    if body.purchase_date is not None:
        h.purchase_date = body.purchase_date
    if body.notes is not None:
        h.notes = body.notes
    await db.commit()
    return await get_portfolio(db, redis, user)


async def delete_holding(
    db: AsyncSession, redis: Redis, user: User, holding_id: int
) -> PortfolioResponse:
    h = await db.scalar(
        select(PortfolioHolding).where(
            PortfolioHolding.id == holding_id, PortfolioHolding.user_id == user.id
        )
    )
    if not h:
        raise HTTPException(status_code=404, detail="Holding not found.")
    db.add(
        PortfolioTransaction(
            user_id=user.id,
            symbol=h.symbol,
            txn_type="sell",
            quantity=h.quantity,
            price=h.avg_buy_price,
            txn_date=date.today(),
        )
    )
    await db.delete(h)
    await db.commit()
    return await get_portfolio(db, redis, user)


async def list_transactions(db: AsyncSession, user: User) -> TransactionListResponse:
    rows = (
        await db.execute(
            select(PortfolioTransaction)
            .where(PortfolioTransaction.user_id == user.id)
            .order_by(desc(PortfolioTransaction.txn_date))
        )
    ).scalars().all()
    return TransactionListResponse(
        items=[
            TransactionItem(
                id=t.id,
                symbol=t.symbol,
                txn_type=t.txn_type,
                quantity=float(t.quantity),
                price=float(t.price),
                txn_date=t.txn_date,
                created_at=t.created_at,
            )
            for t in rows
        ]
    )


def portfolio_to_csv(response: PortfolioResponse) -> str:
    lines = [
        "symbol,quantity,avg_buy_price,purchase_date,ltp,current_value,cost_basis,unrealized_pnl,unrealized_pnl_pct,weight_pct"
    ]
    for h in response.holdings:
        lines.append(
            f"{h.symbol},{h.quantity},{h.avg_buy_price},{h.purchase_date},{h.ltp},{h.current_value},{h.cost_basis},{h.unrealized_pnl},{h.unrealized_pnl_pct},{h.weight_pct}"
        )
    return "\n".join(lines)
