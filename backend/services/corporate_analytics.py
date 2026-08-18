"""Corporate action analytics — DPS, payout ratio, TERP."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.corporate_action import CorporateAction
from backend.models.financial import FinancialLineItem, FinancialPeriod
from backend.schemas.context import (
    CorpActionAnalyticsResponse,
    DpsDataPoint,
    TerpCalculation,
)


async def get_corporate_action_analytics(
    db: AsyncSession, symbol: str
) -> CorpActionAnalyticsResponse:
    sym = symbol.upper()
    ten_years_ago = date.today() - timedelta(days=365 * 10)
    divs = (
        await db.execute(
            select(CorporateAction)
            .where(
                CorporateAction.symbol == sym,
                CorporateAction.action_type.in_(("cash_dividend", "dividend")),
                CorporateAction.ex_date >= ten_years_ago,
            )
            .order_by(CorporateAction.ex_date)
        )
    ).scalars().all()

    dps_series: list[DpsDataPoint] = []
    for d in divs:
        if d.ex_date and d.amount_per_share:
            dps_series.append(
                DpsDataPoint(
                    year=d.ex_date.year,
                    ex_date=d.ex_date,
                    dps=float(d.amount_per_share),
                    payout_ratio=None,
                )
            )

    # Enrich with payout ratio from net profit
    for point in dps_series:
        period = await db.scalar(
            select(FinancialPeriod)
            .where(
                FinancialPeriod.symbol == sym,
                FinancialPeriod.fiscal_year == point.year,
                FinancialPeriod.period_type == "annual",
            )
            .order_by(desc(FinancialPeriod.period_end))
            .limit(1)
        )
        if period:
            np = await db.scalar(
                select(FinancialLineItem.value)
                .where(
                    FinancialLineItem.period_id == period.id,
                    FinancialLineItem.line_code == "net_profit",
                )
            )
            if np and float(np) > 0:
                point.payout_ratio = (point.dps * 1e6) / float(np) * 100

    rights = (
        await db.execute(
            select(CorporateAction)
            .where(
                CorporateAction.symbol == sym,
                CorporateAction.action_type == "rights",
            )
            .order_by(desc(CorporateAction.announced_at))
            .limit(1)
        )
    ).scalar_one_or_none()

    terp: TerpCalculation | None = None
    if rights and rights.ratio and rights.details_json:
        details = rights.details_json or {}
        market_price = details.get("market_price")
        rights_price = details.get("rights_price")
        try:
            ratio_parts = str(rights.ratio).split(":")
            if len(ratio_parts) == 2 and market_price and rights_price:
                existing = int(ratio_parts[0])
                new_shares = int(ratio_parts[1])
                mp = float(market_price)
                rp = float(rights_price)
                terp_val = ((existing * mp) + (new_shares * rp)) / (existing + new_shares)
                terp = TerpCalculation(
                    rights_ratio=rights.ratio,
                    market_price=mp,
                    rights_price=rp,
                    terp=round(terp_val, 2),
                )
        except (ValueError, TypeError):
            pass

    return CorpActionAnalyticsResponse(
        symbol=sym,
        dps_series=dps_series,
        terp=terp,
    )
