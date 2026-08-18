"""Beta and sector-relative return calculations."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from redis.asyncio import Redis
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.price import Price
from backend.models.sector_daily_stats import SectorDailyStats
from backend.models.ticker import Ticker
from backend.schemas.context import BetaResponse


def _daily_returns(prices: list[float]) -> list[float]:
    returns: list[float] = []
    for i in range(1, len(prices)):
        prev = prices[i - 1]
        if prev:
            returns.append((prices[i] - prev) / prev)
    return returns


def _ols_beta(asset_returns: list[float], market_returns: list[float]) -> float | None:
    n = min(len(asset_returns), len(market_returns))
    if n < 30:
        return None
    ar = asset_returns[-n:]
    mr = market_returns[-n:]
    mean_a = sum(ar) / n
    mean_m = sum(mr) / n
    cov = sum((a - mean_a) * (m - mean_m) for a, m in zip(ar, mr, strict=True)) / n
    var_m = sum((m - mean_m) ** 2 for m in mr) / n
    if var_m == 0:
        return None
    return cov / var_m


async def _fetch_close_series(
    db: AsyncSession, symbol: str, days: int = 300
) -> list[tuple[datetime, float]]:
    since = datetime.now(UTC) - timedelta(days=days)
    result = await db.execute(
        select(Price.time, Price.close)
        .where(Price.symbol == symbol, Price.time >= since)
        .order_by(Price.time.asc())
    )
    return [(row.time, float(row.close)) for row in result.all()]


async def compute_beta(db: AsyncSession, symbol: str) -> float | None:
    ticker_series = await _fetch_close_series(db, symbol)
    market_series = await _fetch_close_series(db, "KSE100")
    if len(ticker_series) < 30 or len(market_series) < 30:
        return None
    # Align by date (use last 252 trading days of closes)
    t_prices = [p for _, p in ticker_series][-253:]
    m_prices = [p for _, p in market_series][-253:]
    return _ols_beta(_daily_returns(t_prices), _daily_returns(m_prices))


async def get_beta(
    db: AsyncSession,
    redis: Redis,
    symbol: str,
) -> BetaResponse:
    sym = symbol.upper()
    cache_key = f"ticker:{sym}:beta"
    cached = await redis.get(cache_key)
    if cached:
        return BetaResponse.model_validate(json.loads(cached))

    ticker = await db.get(Ticker, sym)
    beta = await compute_beta(db, sym)
    sector_return_1m = None
    ticker_return_1m = None
    if ticker:
        stats = await db.execute(
            select(SectorDailyStats)
            .where(SectorDailyStats.sector == ticker.sector)
            .order_by(desc(SectorDailyStats.trade_date))
            .limit(1)
        )
        sector_row = stats.scalar_one_or_none()
        if sector_row and sector_row.return_1m is not None:
            sector_return_1m = float(sector_row.return_1m)
        # Ticker 1M return from prices
        month_ago = datetime.now(UTC) - timedelta(days=30)
        prices = await db.execute(
            select(Price.close)
            .where(Price.symbol == sym, Price.time >= month_ago)
            .order_by(Price.time.asc())
        )
        closes = [float(r[0]) for r in prices.all()]
        if len(closes) >= 2 and closes[0]:
            ticker_return_1m = ((closes[-1] - closes[0]) / closes[0]) * 100

    response = BetaResponse(
        symbol=sym,
        beta=beta,
        sector=ticker.sector if ticker else None,
        sector_return_1m=sector_return_1m,
        ticker_return_1m=ticker_return_1m,
    )
    await redis.setex(cache_key, 86400, response.model_dump_json())
    return response
