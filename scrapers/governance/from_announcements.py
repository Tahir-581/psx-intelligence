"""Extract governance data from PSX announcements when SECP is blocked."""

from __future__ import annotations

import re
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.announcement import Announcement
from backend.models.governance import BoardMember, CreditRating


BOARD_PATTERNS = [
    re.compile(r"appointment of (.+?) as (.+?)(?:\.|$)", re.I),
    re.compile(r"resignation of (.+?) from (.+?)(?:\.|$)", re.I),
]

RATING_PATTERNS = [
    (re.compile(r"PACRA.*?([A+-]+(?:\([A-Za-z]+\))?)", re.I), "PACRA"),
    (re.compile(r"VIS.*?([A+-]+(?:\([A-Za-z]+\))?)", re.I), "VIS"),
]


def ingest_governance_from_announcements(session: Session, symbol: str | None = None) -> dict:
    query = select(Announcement).where(
        Announcement.category.in_(("board_change", "credit_rating", "governance"))
    )
    if symbol:
        query = query.where(Announcement.symbol == symbol.upper())
    rows = session.execute(query.order_by(Announcement.published_at.desc()).limit(500)).scalars().all()
    board_count = 0
    rating_count = 0
    for ann in rows:
        text = f"{ann.title} {ann.body_text or ''}"
        if ann.category == "board_change":
            for pat in BOARD_PATTERNS:
                m = pat.search(text)
                if m:
                    name, role = m.group(1).strip(), m.group(2).strip()
                    is_resign = "resignation" in pat.pattern
                    existing = session.execute(
                        select(BoardMember).where(
                            BoardMember.symbol == ann.symbol,
                            BoardMember.name == name,
                            BoardMember.role == role,
                        )
                    ).scalar_one_or_none()
                    if not existing:
                        session.add(
                            BoardMember(
                                symbol=ann.symbol,
                                name=name,
                                role=role,
                                appointment_date=None if is_resign else ann.published_at.date(),
                                resignation_date=ann.published_at.date() if is_resign else None,
                            )
                        )
                        board_count += 1
        if ann.category == "credit_rating":
            for pat, agency in RATING_PATTERNS:
                m = pat.search(text)
                if m:
                    rating = m.group(1)
                    eff = ann.published_at.date()
                    dup = session.execute(
                        select(CreditRating).where(
                            CreditRating.symbol == ann.symbol,
                            CreditRating.agency == agency,
                            CreditRating.effective_date == eff,
                        )
                    ).scalar_one_or_none()
                    if not dup:
                        session.add(
                            CreditRating(
                                symbol=ann.symbol,
                                agency=agency,
                                rating=rating,
                                effective_date=eff,
                                source_url=ann.source_url,
                            )
                        )
                        rating_count += 1
    session.commit()
    return {"board_added": board_count, "ratings_added": rating_count}
