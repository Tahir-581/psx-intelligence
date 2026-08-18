from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from backend.models.announcement import Announcement
from backend.models.material_event import MaterialEvent
from parsers.material_events import parse_material_events
from scrapers.psx.announcements import get_sync_session, record_scraper_run


def upsert_material_events(session: Session, rows: list[dict]) -> int:
    if not rows:
        return 0
    stmt = insert(MaterialEvent).values(rows)
    stmt = stmt.on_conflict_do_nothing(constraint="uq_material_events_key")
    result = session.execute(stmt)
    session.commit()
    return result.rowcount or 0


def extract_from_announcements(
    session: Session,
    announcements: list[Announcement],
) -> int:
    all_rows: list[dict] = []
    for ann in announcements:
        parsed = parse_material_events(
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
                    "event_type": p.event_type,
                    "headline": p.headline,
                    "event_date": p.event_date,
                    "counterparty": p.counterparty,
                    "amount_pkr": p.amount_pkr,
                    "significance_score": p.significance_score,
                    "summary": p.summary,
                    "source_announcement_id": p.source_announcement_id,
                }
            )
    return upsert_material_events(session, all_rows)


def run_extract_material_events(
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
            "extract_material_events",
            success=True,
            records=ingested,
        )
        session.commit()
        return {"extracted": ingested, "announcements_processed": len(announcements)}
    except Exception as exc:
        session.rollback()
        record_scraper_run(
            session,
            "extract_material_events",
            success=False,
            error=str(exc)[:500],
        )
        session.commit()
        raise
    finally:
        session.close()
