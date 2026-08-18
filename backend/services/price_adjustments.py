"""Split/bonus-adjusted price series from corporate actions."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.corporate_action import CorporateAction
from backend.schemas.market import PriceBar


async def get_adjustment_factors(
    db: AsyncSession, symbol: str
) -> list[tuple[datetime, float]]:
    """Return (ex_date, cumulative_factor) for splits and bonuses, newest first."""
    result = await db.execute(
        select(CorporateAction)
        .where(
            CorporateAction.symbol == symbol.upper(),
            CorporateAction.action_type.in_(("split", "bonus", "stock_dividend")),
        )
        .order_by(CorporateAction.ex_date.desc())
    )
    factors: list[tuple[datetime, float]] = []
    cumulative = 1.0
    for action in result.scalars().all():
        if action.ex_date is None:
            continue
        ex_dt = datetime.combine(action.ex_date, datetime.min.time())
        try:
            ratio = float(action.ratio) if action.ratio else 1.0
        except (TypeError, ValueError):
            ratio = 1.0
        if action.action_type == "split" and ratio > 0:
            cumulative *= ratio
        elif action.action_type in ("bonus", "stock_dividend") and ratio > 0:
            cumulative *= 1 + ratio
        factors.append((ex_dt, cumulative))
    return factors


def apply_adjustments(bars: list[PriceBar], factors: list[tuple[datetime, float]]) -> list[PriceBar]:
    """Backward-adjust prices for splits/bonus."""
    if not factors:
        return bars
    adjusted: list[PriceBar] = []
    for bar in bars:
        factor = 1.0
        for ex_dt, cum in factors:
            if bar.time < ex_dt:
                factor = cum
                break
        adjusted.append(
            PriceBar(
                time=bar.time,
                open=bar.open / factor,
                high=bar.high / factor,
                low=bar.low / factor,
                close=bar.close / factor,
                volume=int(bar.volume * factor),
            )
        )
    return adjusted
