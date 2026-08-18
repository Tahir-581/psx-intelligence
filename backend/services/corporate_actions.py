from datetime import date

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.corporate_action import CorporateAction
from backend.schemas.context import (
    CorporateActionItem,
    CorporateActionListResponse,
    CorporateCalendarItem,
    CorporateCalendarResponse,
)


async def get_corporate_actions(
    db: AsyncSession, symbol: str
) -> CorporateActionListResponse:
    result = await db.execute(
        select(CorporateAction)
        .where(CorporateAction.symbol == symbol)
        .order_by(desc(CorporateAction.announced_at))
    )
    items = [
        CorporateActionItem(
            id=row.id,
            symbol=row.symbol,
            action_type=row.action_type,
            announced_at=row.announced_at,
            ex_date=row.ex_date,
            record_date=row.record_date,
            payment_date=row.payment_date,
            amount_per_share=float(row.amount_per_share) if row.amount_per_share else None,
            ratio=row.ratio,
            currency=row.currency,
            source_announcement_id=row.source_announcement_id,
        )
        for row in result.scalars().all()
    ]
    return CorporateActionListResponse(items=items)


async def get_corporate_calendar(
    db: AsyncSession,
    *,
    from_date: date | None = None,
    to_date: date | None = None,
) -> CorporateCalendarResponse:
    query = select(CorporateAction).where(
        CorporateAction.action_type.in_(("cash_dividend", "agm", "egm", "book_closure"))
    )
    if from_date:
        query = query.where(CorporateAction.ex_date >= from_date)
    if to_date:
        query = query.where(CorporateAction.ex_date <= to_date)
    result = await db.execute(query.order_by(CorporateAction.ex_date.asc().nullslast()))
    items = [
        CorporateCalendarItem(
            symbol=row.symbol,
            action_type=row.action_type,
            announced_at=row.announced_at,
            ex_date=row.ex_date,
            record_date=row.record_date,
            amount_per_share=float(row.amount_per_share) if row.amount_per_share else None,
            ratio=row.ratio,
        )
        for row in result.scalars().all()
    ]
    return CorporateCalendarResponse(items=items)


async def get_next_dividend_ex_date(db: AsyncSession, symbol: str) -> date | None:
    today = date.today()
    result = await db.execute(
        select(CorporateAction.ex_date)
        .where(
            CorporateAction.symbol == symbol,
            CorporateAction.action_type == "cash_dividend",
            CorporateAction.ex_date.is_not(None),
            CorporateAction.ex_date >= today,
        )
        .order_by(CorporateAction.ex_date.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()
