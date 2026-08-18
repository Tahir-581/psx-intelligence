"""Ticker overview BFF — aggregates key dashboard data."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from backend.schemas.overview import OverviewNewsItem, OverviewResponse
from backend.services.chart_markers import get_chart_markers
from backend.services.corporate_actions import get_corporate_actions, get_next_dividend_ex_date
from backend.services.fundamentals import get_announcements, get_ratios
from backend.services.governance import has_board_change_30d
from backend.services.intelligence import get_weekly_summary
from backend.services.news import get_ticker_news


async def get_overview(db: AsyncSession, symbol: str) -> OverviewResponse:
    sym = symbol.upper()
    summary = await get_weekly_summary(db, sym)
    ratios = await get_ratios(db, sym)
    key_ratios = ratios.latest[:8]
    next_ex = await get_next_dividend_ex_date(db, sym)
    actions = await get_corporate_actions(db, sym)
    upcoming = [
        {
            "action_type": a.action_type,
            "ex_date": a.ex_date.isoformat() if a.ex_date else None,
            "amount_per_share": a.amount_per_share,
        }
        for a in actions.items
        if a.ex_date and a.ex_date >= date.today()
    ][:5]
    announcements = await get_announcements(db, sym, page=1, page_size=5)
    news = await get_ticker_news(db, sym, page=1, page_size=3, include_pro_fields=True)
    markers = await get_chart_markers(
        db, sym, from_dt=datetime.now(UTC) - timedelta(days=365)
    )
    return OverviewResponse(
        symbol=sym,
        ai_summary=summary,
        key_ratios=key_ratios,
        next_dividend_ex_date=next_ex,
        upcoming_actions=upcoming,
        recent_announcements=announcements.items,
        recent_news=[
            OverviewNewsItem(
                id=n.id,
                headline=n.headline,
                source=n.source,
                published_at=n.published_at,
            )
            for n in news.items
        ],
        board_change_30d=await has_board_change_30d(db, sym),
        delisting_detected=markers.delisting_detected,
        delisting_title=markers.delisting_title,
    )
