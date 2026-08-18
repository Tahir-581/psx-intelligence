"""Governance and credit rating services."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.announcement import Announcement
from backend.models.governance import BoardMember, CreditRating, SecpFiling
from backend.schemas.governance import (
    BoardMemberItem,
    CreditRatingItem,
    CreditRatingsResponse,
    GovernanceResponse,
    SecpFilingItem,
)


async def has_board_change_30d(db: AsyncSession, symbol: str) -> bool:
    cutoff = date.today() - timedelta(days=30)
    result = await db.execute(
        select(BoardMember.id).where(
            BoardMember.symbol == symbol.upper(),
            (
                (BoardMember.appointment_date >= cutoff)
                | (BoardMember.resignation_date >= cutoff)
            ),
        ).limit(1)
    )
    if result.scalar_one_or_none():
        return True
    ann = await db.execute(
        select(Announcement.id).where(
            Announcement.symbol == symbol.upper(),
            Announcement.category == "board_change",
            Announcement.published_at >= datetime.now(UTC) - timedelta(days=30),
        ).limit(1)
    )
    return ann.scalar_one_or_none() is not None


async def get_governance(db: AsyncSession, symbol: str) -> GovernanceResponse:
    sym = symbol.upper()
    board_rows = (
        await db.execute(
            select(BoardMember)
            .where(BoardMember.symbol == sym, BoardMember.resignation_date.is_(None))
            .order_by(BoardMember.role, BoardMember.name)
        )
    ).scalars().all()

    recent_changes = (
        await db.execute(
            select(BoardMember)
            .where(
                BoardMember.symbol == sym,
                (
                    (BoardMember.appointment_date >= date.today() - timedelta(days=365))
                    | (BoardMember.resignation_date >= date.today() - timedelta(days=365))
                ),
            )
            .order_by(desc(BoardMember.appointment_date))
        )
    ).scalars().all()

    filings = (
        await db.execute(
            select(SecpFiling)
            .where(SecpFiling.symbol == sym)
            .order_by(desc(SecpFiling.filed_at))
            .limit(20)
        )
    ).scalars().all()

    ccg_items = [
        "Board independence disclosure",
        "Audit committee charter",
        "Related party transactions policy",
        "Code of conduct",
        "Whistleblower mechanism",
    ]
    filed_types = {f.form_type for f in filings}
    ccg_checklist = [
        {"item": item, "filed": any(t in item.lower() for t in filed_types) or len(filings) > 0}
        for item in ccg_items
    ]

    return GovernanceResponse(
        symbol=sym,
        board=[
            BoardMemberItem(
                name=b.name,
                role=b.role,
                appointment_date=b.appointment_date,
                resignation_date=b.resignation_date,
            )
            for b in board_rows
        ],
        director_changes=[
            BoardMemberItem(
                name=b.name,
                role=b.role,
                appointment_date=b.appointment_date,
                resignation_date=b.resignation_date,
            )
            for b in recent_changes
        ],
        board_change_30d=await has_board_change_30d(db, sym),
        filings=[
            SecpFilingItem(
                form_type=f.form_type,
                filed_at=f.filed_at,
                raw_url=f.raw_url,
            )
            for f in filings
        ],
        ccg_checklist=ccg_checklist,
    )


async def get_credit_ratings(db: AsyncSession, symbol: str) -> CreditRatingsResponse:
    sym = symbol.upper()
    rows = (
        await db.execute(
            select(CreditRating)
            .where(CreditRating.symbol == sym)
            .order_by(desc(CreditRating.effective_date))
        )
    ).scalars().all()
    return CreditRatingsResponse(
        symbol=sym,
        ratings=[
            CreditRatingItem(
                agency=r.agency,
                rating=r.rating,
                outlook=r.outlook,
                effective_date=r.effective_date,
                source_url=r.source_url,
            )
            for r in rows
        ],
    )
