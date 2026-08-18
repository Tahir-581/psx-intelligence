import os
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import create_engine, delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from backend.config import settings
from backend.models.announcement import Announcement
from backend.models.financial import FinancialLineItem, FinancialPeriod
from backend.models.insider_trade import InsiderTrade
from backend.models.ownership import OwnershipSnapshot
from backend.models.parser_review import ParserReviewQueue
from backend.models.scraper_run import ScraperRun
from parsers.confidence import needs_review, score_insider_parse
from parsers.download import download_pdf
from parsers.pdf_financials import parse_financial_pdf
from parsers.pdf_insider import parse_insider_pdf
from parsers.pdf_ownership import parse_ownership_pdf


def get_sync_session() -> Session:
    engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
    return sessionmaker(bind=engine)()


def record_scraper_run(
    session: Session,
    scraper_name: str,
    *,
    success: bool,
    records: int = 0,
    error: str | None = None,
) -> None:
    now = datetime.now(UTC)
    session.add(
        ScraperRun(
            scraper_name=scraper_name,
            last_success_at=now if success else None,
            last_run_at=now,
            records_ingested=records,
            error_message=error,
        )
    )


def _already_parsed(session: Session, ann: Announcement) -> bool:
    if not ann.pdf_url:
        return True
    pdf = ann.pdf_url
    if session.scalar(
        select(FinancialPeriod.id).where(FinancialPeriod.source_pdf_url == pdf).limit(1)
    ):
        return True
    if session.scalar(
        select(InsiderTrade.id)
        .where(InsiderTrade.source_announcement_id == ann.id)
        .limit(1)
    ):
        return True
    if session.scalar(
        select(OwnershipSnapshot.id).where(OwnershipSnapshot.source_pdf_url == pdf).limit(1)
    ):
        return True
    return False


def _queue_review(
    session: Session,
    *,
    source_type: str,
    source_url: str,
    symbol: str | None,
    confidence: float,
    excerpt: str,
) -> None:
    session.add(
        ParserReviewQueue(
            source_type=source_type,
            source_url=source_url,
            symbol=symbol,
            confidence=Decimal(str(confidence)),
            status="pending",
            raw_excerpt=excerpt[:2000],
        )
    )


def _upsert_financial(session: Session, ann: Announcement, parsed) -> bool:
    stmt = insert(FinancialPeriod).values(
        symbol=ann.symbol,
        period_end=parsed.period_end,
        period_type=parsed.period_type,
        fiscal_year=parsed.fiscal_year,
        fiscal_quarter=parsed.fiscal_quarter,
        currency=parsed.currency,
        source_pdf_url=ann.pdf_url,
        parser_confidence=Decimal(str(parsed.confidence)),
        is_verified=not needs_review(parsed.confidence),
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_fin_periods",
        set_={
            "parser_confidence": stmt.excluded.parser_confidence,
            "is_verified": stmt.excluded.is_verified,
            "source_pdf_url": stmt.excluded.source_pdf_url,
        },
    ).returning(FinancialPeriod.id)
    period_id = session.scalar(stmt)
    if not period_id:
        period_id = session.scalar(
            select(FinancialPeriod.id).where(
                FinancialPeriod.symbol == ann.symbol,
                FinancialPeriod.period_end == parsed.period_end,
                FinancialPeriod.period_type == parsed.period_type,
            )
        )
    if not period_id:
        return False
    for item in parsed.line_items:
        li_stmt = insert(FinancialLineItem).values(
            period_id=period_id,
            line_code=item.line_code,
            value=item.value,
            unit=item.unit,
        )
        li_stmt = li_stmt.on_conflict_do_update(
            constraint="uq_fin_line_items",
            set_={"value": li_stmt.excluded.value, "unit": li_stmt.excluded.unit},
        )
        session.execute(li_stmt)
    if needs_review(parsed.confidence):
        _queue_review(
            session,
            source_type="financial_result",
            source_url=ann.pdf_url or "",
            symbol=ann.symbol,
            confidence=parsed.confidence,
            excerpt=ann.title,
        )
    return True


def _upsert_insider(session: Session, ann: Announcement, trades: list) -> bool:
    confidence = score_insider_parse(trades)
    ingested = False
    for trade in trades:
        session.add(
            InsiderTrade(
                symbol=ann.symbol,
                director_name=trade.director_name,
                designation=trade.designation,
                transaction_date=trade.transaction_date,
                transaction_type=trade.transaction_type,
                shares=trade.shares,
                price_per_share=trade.price_per_share,
                post_holding_shares=trade.post_holding_shares,
                source_announcement_id=ann.id,
            )
        )
        ingested = True
    if needs_review(confidence):
        _queue_review(
            session,
            source_type="insider_trade",
            source_url=ann.pdf_url or "",
            symbol=ann.symbol,
            confidence=confidence,
            excerpt=ann.title,
        )
    return ingested


def _upsert_ownership(session: Session, ann: Announcement, parsed) -> bool:
    for row in parsed.rows:
        stmt = insert(OwnershipSnapshot).values(
            symbol=ann.symbol,
            as_of_date=parsed.as_of_date,
            holder_category=row.holder_category,
            shares=row.shares,
            pct_outstanding=row.pct_outstanding,
            source_pdf_url=ann.pdf_url,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_ownership_snap",
            set_={
                "shares": stmt.excluded.shares,
                "pct_outstanding": stmt.excluded.pct_outstanding,
                "source_pdf_url": stmt.excluded.source_pdf_url,
            },
        )
        session.execute(stmt)
    if needs_review(parsed.confidence):
        _queue_review(
            session,
            source_type="pattern_of_shareholding",
            source_url=ann.pdf_url or "",
            symbol=ann.symbol,
            confidence=parsed.confidence,
            excerpt=ann.title,
        )
    return bool(parsed.rows)


def _route_category(category: str, title: str) -> str:
    cat = category.lower()
    title_lower = title.lower()
    if cat in {"financial_result", "financial_results"} or "financial result" in title_lower:
        return "financial"
    if cat == "insider_trade" or "insider" in title_lower:
        return "insider"
    if cat in {"pattern_of_shareholding", "ownership"} or "shareholding" in title_lower:
        return "ownership"
    return "skip"


def _period_line_count(session: Session, pdf_url: str) -> int:
    period_id = session.scalar(
        select(FinancialPeriod.id).where(FinancialPeriod.source_pdf_url == pdf_url).limit(1)
    )
    if not period_id:
        return -1
    return (
        session.scalar(
            select(func.count())
            .select_from(FinancialLineItem)
            .where(FinancialLineItem.period_id == period_id)
        )
        or 0
    )


def _delete_empty_period(session: Session, pdf_url: str) -> None:
    period_id = session.scalar(
        select(FinancialPeriod.id).where(FinancialPeriod.source_pdf_url == pdf_url).limit(1)
    )
    if not period_id:
        return
    count = session.scalar(
        select(func.count())
        .select_from(FinancialLineItem)
        .where(FinancialLineItem.period_id == period_id)
    )
    if count:
        return
    session.execute(delete(FinancialPeriod).where(FinancialPeriod.id == period_id))


def reparse_financial_pdfs(
    *,
    symbols: list[str] | None = None,
    limit: int | None = None,
    force: bool = False,
) -> dict:
    session = get_sync_session()
    ingested = processed = skipped = 0
    try:
        query = (
            select(Announcement)
            .where(
                Announcement.pdf_url.isnot(None),
                or_(
                    Announcement.category.in_(["financial_result", "financial_results"]),
                    Announcement.title.ilike("%financial result%"),
                    Announcement.title.ilike("%quarterly report%"),
                ),
            )
            .order_by(Announcement.published_at.desc())
        )
        if symbols:
            query = query.where(Announcement.symbol.in_(symbols))
        if limit:
            query = query.limit(limit)
        announcements = session.scalars(query).all()

        for ann in announcements:
            if not ann.pdf_url:
                continue
            existing_lines = _period_line_count(session, ann.pdf_url)
            if existing_lines > 0 and not force:
                skipped += 1
                continue
            if existing_lines == 0:
                _delete_empty_period(session, ann.pdf_url)

            pdf_path = None
            try:
                pdf_path = download_pdf(ann.pdf_url)
                processed += 1
                parsed = parse_financial_pdf(pdf_path, ann.symbol, ann.title)
                if parsed and parsed.line_items and _upsert_financial(session, ann, parsed):
                    ingested += 1
                    session.commit()
            except Exception:
                session.rollback()
                continue
            finally:
                if pdf_path and pdf_path.exists():
                    try:
                        os.unlink(pdf_path)
                    except OSError:
                        pass

        record_scraper_run(session, "reparse_financial_pdfs", success=True, records=ingested)
        session.commit()
        return {
            "candidates": len(announcements),
            "processed": processed,
            "ingested": ingested,
            "skipped": skipped,
        }
    except Exception as exc:
        session.rollback()
        record_scraper_run(session, "reparse_financial_pdfs", success=False, error=str(exc))
        session.commit()
        raise
    finally:
        session.close()


def run_reparse_financial_pdfs(
    *,
    symbols: list[str] | None = None,
    limit: int | None = None,
    force: bool = False,
) -> dict:
    return reparse_financial_pdfs(symbols=symbols, limit=limit, force=force)


def parse_pending_pdfs(limit: int = 50) -> dict:
    session = get_sync_session()
    ingested = 0
    try:
        announcements = session.scalars(
            select(Announcement)
            .where(Announcement.pdf_url.isnot(None))
            .where(
                or_(
                    Announcement.category.in_(
                        [
                            "financial_result",
                            "insider_trade",
                            "pattern_of_shareholding",
                            "dividend",
                        ]
                    ),
                    Announcement.title.ilike("%financial result%"),
                    Announcement.title.ilike("%insider%"),
                    Announcement.title.ilike("%shareholding%"),
                )
            )
            .order_by(Announcement.published_at.desc())
            .limit(limit * 3)
        ).all()

        processed = 0
        for ann in announcements:
            if processed >= limit:
                break
            if _already_parsed(session, ann):
                continue
            route = _route_category(ann.category, ann.title)
            if route == "skip":
                continue
            pdf_path = None
            try:
                pdf_path = download_pdf(ann.pdf_url)  # type: ignore[arg-type]
                processed += 1
                if route == "financial":
                    parsed = parse_financial_pdf(pdf_path, ann.symbol, ann.title)
                    if parsed and _upsert_financial(session, ann, parsed):
                        ingested += 1
                elif route == "insider":
                    trades = parse_insider_pdf(pdf_path)
                    if trades and _upsert_insider(session, ann, trades):
                        ingested += 1
                elif route == "ownership":
                    parsed = parse_ownership_pdf(pdf_path, ann.symbol, ann.title)
                    if parsed and _upsert_ownership(session, ann, parsed):
                        ingested += 1
            except Exception:
                continue
            finally:
                if pdf_path and pdf_path.exists():
                    try:
                        os.unlink(pdf_path)
                    except OSError:
                        pass

        record_scraper_run(session, "parse_pending_pdfs", success=True, records=ingested)
        session.commit()
        return {"ingested": ingested, "processed": processed}
    except Exception as exc:
        session.rollback()
        record_scraper_run(session, "parse_pending_pdfs", success=False, error=str(exc))
        session.commit()
        raise
    finally:
        session.close()


def run_parse_pending_pdfs(limit: int = 50) -> dict:
    return parse_pending_pdfs(limit=limit)
