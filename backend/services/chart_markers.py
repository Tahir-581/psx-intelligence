"""Unified chart marker payloads for ticker price charts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.announcement import Announcement
from backend.models.corporate_action import CorporateAction
from backend.models.insider_trade import InsiderTrade
from backend.models.macro_series import MacroSeries
from backend.models.material_event import MaterialEvent
from backend.models.news_article import NewsArticle
from backend.models.news_article_ticker import NewsArticleTicker
from backend.schemas.market import ChartMarkerItem, ChartMarkersResponse


async def get_chart_markers(
    db: AsyncSession,
    symbol: str,
    *,
    from_dt: datetime | None = None,
    to_dt: datetime | None = None,
) -> ChartMarkersResponse:
    sym = symbol.upper()
    if not from_dt:
        from_dt = datetime.now(UTC) - timedelta(days=365)
    if not to_dt:
        to_dt = datetime.now(UTC)

    markers: list[ChartMarkerItem] = []

    divs = await db.execute(
        select(CorporateAction).where(
            CorporateAction.symbol == sym,
            CorporateAction.action_type.in_(("cash_dividend", "dividend")),
            CorporateAction.ex_date.isnot(None),
            CorporateAction.ex_date >= from_dt.date(),
            CorporateAction.ex_date <= to_dt.date(),
        )
    )
    for d in divs.scalars().all():
        markers.append(
            ChartMarkerItem(
                time=datetime.combine(d.ex_date, datetime.min.time()),
                label=f"Dividend {d.amount_per_share or ''}",
                kind="dividend",
                significance=1,
            )
        )

    insiders = await db.execute(
        select(InsiderTrade).where(
            InsiderTrade.symbol == sym,
            InsiderTrade.transaction_date >= from_dt.date(),
            InsiderTrade.transaction_date <= to_dt.date(),
        )
    )
    for t in insiders.scalars().all():
        markers.append(
            ChartMarkerItem(
                time=datetime.combine(t.transaction_date, datetime.min.time()),
                label=f"{t.transaction_type} {t.shares:,} @ {t.price_per_share or 'N/A'}",
                kind="insider",
                significance=2 if t.transaction_type == "buy" else 1,
            )
        )

    events = await db.execute(
        select(MaterialEvent).where(
            MaterialEvent.symbol == sym,
            MaterialEvent.event_date >= from_dt.date(),
            MaterialEvent.event_date <= to_dt.date(),
        )
    )
    for e in events.scalars().all():
        markers.append(
            ChartMarkerItem(
                time=datetime.combine(e.event_date, datetime.min.time()),
                label=e.headline[:80],
                kind="event",
                significance=e.significance_score or 1,
            )
        )

    macro = await db.execute(
        select(MacroSeries).where(
            MacroSeries.series_code == "SBP_POLICY_RATE",
            MacroSeries.time >= from_dt,
            MacroSeries.time <= to_dt,
        )
    )
    prev_rate: float | None = None
    for m in sorted(macro.scalars().all(), key=lambda x: x.time):
        val = float(m.value)
        if prev_rate is not None and val != prev_rate:
            markers.append(
                ChartMarkerItem(
                    time=m.time,
                    label=f"SBP rate → {val}%",
                    kind="macro",
                    significance=3,
                )
            )
        prev_rate = val

    news_counts = await db.execute(
        select(
            func.date(NewsArticle.published_at).label("day"),
            func.count(NewsArticle.id).label("cnt"),
        )
        .join(NewsArticleTicker, NewsArticleTicker.article_id == NewsArticle.id)
        .where(
            NewsArticleTicker.symbol == sym,
            NewsArticle.published_at >= from_dt,
            NewsArticle.published_at <= to_dt,
        )
        .group_by(func.date(NewsArticle.published_at))
        .having(func.count(NewsArticle.id) >= 3)
    )
    for row in news_counts.all():
        markers.append(
            ChartMarkerItem(
                time=datetime.combine(row.day, datetime.min.time()),
                label=f"{row.cnt} news articles",
                kind="news",
                significance=1,
            )
        )

    delisting = await db.execute(
        select(Announcement).where(
            Announcement.symbol == sym,
            Announcement.category.in_(("delisting", "show_cause")),
            Announcement.published_at >= from_dt,
        ).limit(1)
    )
    delist_row = delisting.scalar_one_or_none()

    return ChartMarkersResponse(
        symbol=sym,
        markers=sorted(markers, key=lambda m: m.time),
        delisting_detected=delist_row is not None,
        delisting_title=delist_row.title if delist_row else None,
    )
