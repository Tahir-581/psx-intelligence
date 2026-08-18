from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.material_event import MaterialEvent
from backend.models.ticker import Ticker
from backend.schemas.context import MaterialEventItem, MaterialEventListResponse


def _link_counterparty(db_tickers: dict[str, str], counterparty: str | None) -> str | None:
    if not counterparty:
        return None
    cp_upper = counterparty.upper()
    for sym, name in db_tickers.items():
        if sym in cp_upper or name.upper() in cp_upper:
            return sym
    return None


async def get_material_events(
    db: AsyncSession,
    symbol: str,
    *,
    min_significance: int = 1,
) -> MaterialEventListResponse:
    tickers = (await db.execute(select(Ticker.symbol, Ticker.name))).all()
    ticker_map = {r.symbol: r.name for r in tickers}

    result = await db.execute(
        select(MaterialEvent)
        .where(
            MaterialEvent.symbol == symbol,
            MaterialEvent.significance_score >= min_significance,
        )
        .order_by(desc(MaterialEvent.significance_score), desc(MaterialEvent.event_date))
    )
    items = [
        MaterialEventItem(
            id=row.id,
            symbol=row.symbol,
            event_type=row.event_type,
            headline=row.headline,
            event_date=row.event_date,
            counterparty=row.counterparty,
            amount_pkr=float(row.amount_pkr) if row.amount_pkr else None,
            significance_score=row.significance_score,
            summary=row.summary,
            source_announcement_id=row.source_announcement_id,
            linked_symbol=_link_counterparty(ticker_map, row.counterparty),
        )
        for row in result.scalars().all()
    ]
    return MaterialEventListResponse(items=items)
