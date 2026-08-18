"""Compare and peers APIs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from redis.asyncio import Redis
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.entitlements import compare_symbol_limit
from backend.models.computed_ratio import ComputedRatio
from backend.models.price import Price
from backend.models.ticker import Ticker
from backend.models.user import User
from backend.schemas.compare import (
    CompareRatioRow,
    CompareResponse,
    NormalizedSeries,
    NormalizedSeriesPoint,
    PeerRow,
    PeersResponse,
)
from backend.services.cache import cache_get_json, cache_set_json
from backend.services.fundamentals import get_latest_ratio_map


async def get_compare(
    db: AsyncSession,
    redis: Redis,
    symbols: list[str],
    user: User | None,
) -> CompareResponse:
    syms = [s.upper() for s in symbols]
    limit = compare_symbol_limit(user)
    if len(syms) < 2:
        raise HTTPException(status_code=422, detail="At least 2 symbols required.")
    if len(syms) > limit:
        raise HTTPException(
            status_code=403,
            detail=f"Compare limited to {limit} symbols. Upgrade to Pro for up to 4.",
        )

    cache_key = f"compare:{':'.join(sorted(syms))}"
    cached = await cache_get_json(redis, cache_key)
    if cached:
        return CompareResponse(**cached)

    tickers = []
    for sym in syms:
        t = await db.get(Ticker, sym)
        if not t:
            raise HTTPException(status_code=404, detail=f"Symbol {sym} not found.")
        tickers.append(t)

    series_list: list[NormalizedSeries] = []
    common_start: datetime | None = None
    for sym in syms:
        rows = (
            await db.execute(
                select(Price.time, Price.close)
                .where(Price.symbol == sym)
                .order_by(Price.time.asc())
            )
        ).all()
        if not rows:
            continue
        start = rows[0][0]
        if common_start is None or start > common_start:
            common_start = start

    if not common_start:
        raise HTTPException(status_code=404, detail="No price data for symbols.")

    for sym in syms:
        rows = (
            await db.execute(
                select(Price.time, Price.close)
                .where(Price.symbol == sym, Price.time >= common_start)
                .order_by(Price.time.asc())
            )
        ).all()
        if not rows:
            continue
        base = float(rows[0][1])
        points = [
            NormalizedSeriesPoint(date=r[0].date(), value=round(float(r[1]) / base * 100, 2))
            for r in rows
        ]
        t = await db.get(Ticker, sym)
        series_list.append(
            NormalizedSeries(
                symbol=sym,
                name=t.name if t else sym,
                sector=t.sector if t else None,
                points=points,
            )
        )

    ratio_codes = ["pe_ttm", "roe", "debt_to_equity", "dividend_yield", "net_margin"]
    ratio_rows: list[CompareRatioRow] = []
    for code in ratio_codes:
        values: dict[str, float | None] = {}
        for sym in syms:
            ratios = await get_latest_ratio_map(db, sym)
            values[sym] = ratios.get(code)
        ratio_rows.append(CompareRatioRow(ratio_code=code, values=values))

    response = CompareResponse(symbols=syms, series=series_list, ratios=ratio_rows)
    await cache_set_json(redis, cache_key, response.model_dump(mode="json"), 86400)
    return response


async def get_peers(db: AsyncSession, redis: Redis, symbol: str) -> PeersResponse:
    sym = symbol.upper()
    cache_key = f"ticker:{sym}:peers"
    cached = await cache_get_json(redis, cache_key)
    if cached:
        return PeersResponse(**cached)

    ticker = await db.get(Ticker, sym)
    if not ticker:
        raise HTTPException(status_code=404, detail="Symbol not found.")

    peers_q = (
        select(Ticker)
        .where(Ticker.sector == ticker.sector, Ticker.is_active.is_(True), Ticker.is_debt.is_(False))
        .order_by(Ticker.shares_outstanding.desc().nullslast())
        .limit(15)
    )
    peers = (await db.execute(peers_q)).scalars().all()

    rows: list[PeerRow] = []
    pe_vals: list[float] = []
    roe_vals: list[float] = []
    de_vals: list[float] = []
    dy_vals: list[float] = []
    ret_vals: list[float] = []

    since_1m = datetime.now(UTC) - timedelta(days=30)

    for p in peers:
        ratios = await get_latest_ratio_map(db, p.symbol)
        latest = await db.scalar(
            select(Price.close)
            .where(Price.symbol == p.symbol)
            .order_by(desc(Price.time))
            .limit(1)
        )
        past = await db.scalar(
            select(Price.close)
            .where(Price.symbol == p.symbol, Price.time <= since_1m)
            .order_by(desc(Price.time))
            .limit(1)
        )
        ret_1m = None
        if latest and past and float(past):
            ret_1m = round((float(latest) - float(past)) / float(past) * 100, 2)

        mc = None
        if latest and p.shares_outstanding:
            mc = float(latest) * p.shares_outstanding

        row = PeerRow(
            symbol=p.symbol,
            name=p.name,
            market_cap=mc,
            pe_ttm=ratios.get("pe_ttm"),
            roe=ratios.get("roe"),
            debt_to_equity=ratios.get("debt_to_equity"),
            dividend_yield=ratios.get("dividend_yield"),
            return_1m=ret_1m,
        )
        rows.append(row)
        if row.pe_ttm is not None:
            pe_vals.append(row.pe_ttm)
        if row.roe is not None:
            roe_vals.append(row.roe)
        if row.debt_to_equity is not None:
            de_vals.append(row.debt_to_equity)
        if row.dividend_yield is not None:
            dy_vals.append(row.dividend_yield)
        if row.return_1m is not None:
            ret_vals.append(row.return_1m)

    def _median(vals: list[float]) -> float | None:
        if not vals:
            return None
        s = sorted(vals)
        mid = len(s) // 2
        return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2

    median_row = PeerRow(
        symbol="SECTOR_MEDIAN",
        name="Sector median",
        market_cap=None,
        pe_ttm=_median(pe_vals),
        roe=_median(roe_vals),
        debt_to_equity=_median(de_vals),
        dividend_yield=_median(dy_vals),
        return_1m=_median(ret_vals),
    )

    response = PeersResponse(
        symbol=sym,
        sector=ticker.sector,
        peers=rows,
        sector_median=median_row,
    )
    await cache_set_json(redis, cache_key, response.model_dump(mode="json"), 86400)
    return response
