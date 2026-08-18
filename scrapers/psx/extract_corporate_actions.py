from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from backend.models.announcement import Announcement
from backend.models.corporate_action import CorporateAction
from parsers.corporate_actions import parse_corporate_actions
from scrapers.psx.announcements import get_sync_session, record_scraper_run


def upsert_corporate_actions(session: Session, rows: list[dict]) -> int:
    if not rows:
        return 0
    stmt = insert(CorporateAction).values(rows)
    stmt = stmt.on_conflict_do_nothing(constraint="uq_corporate_actions_key")
    result = session.execute(stmt)
    session.commit()
    return result.rowcount or 0


def extract_from_announcements(
    session: Session,
    announcements: list[Announcement],
) -> int:
    all_rows: list[dict] = []
    for ann in announcements:
        parsed = parse_corporate_actions(
            symbol=ann.symbol,
            title=ann.title,
            body_text=ann.body_text,
            category=ann.category,
            published_at=ann.published_at,
            source_announcement_id=ann.id,
        )
        for p in parsed:
            all_rows.append(
                {
                    "symbol": p.symbol,
                    "action_type": p.action_type,
                    "announced_at": p.announced_at,
                    "ex_date": p.ex_date,
                    "record_date": p.record_date,
                    "payment_date": p.payment_date,
                    "amount_per_share": p.amount_per_share,
                    "ratio": p.ratio,
                    "currency": p.currency,
                    "source_announcement_id": p.source_announcement_id,
                    "details_json": p.details_json,
                }
            )
    return upsert_corporate_actions(session, all_rows)


def run_extract_corporate_actions(
    symbols: list[str] | None = None,
    limit: int | None = None,
) -> dict:
    session = get_sync_session()
    try:
        q = select(Announcement).order_by(Announcement.published_at.desc())
        if symbols:
            q = q.where(Announcement.symbol.in_(symbols))
        if limit:
            q = q.limit(limit)
        announcements = list(session.scalars(q).all())
        ingested = extract_from_announcements(session, announcements)
        record_scraper_run(
            session,
            "extract_corporate_actions",
            success=True,
            records=ingested,
        )
        session.commit()
        return {"extracted": ingested, "announcements_processed": len(announcements)}
    except Exception as exc:
        session.rollback()
        record_scraper_run(
            session,
            "extract_corporate_actions",
            success=False,
            error=str(exc)[:500],
        )
        session.commit()
        raise
    finally:
        session.close()
