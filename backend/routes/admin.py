from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.models.ingest import FailedCeleryTask
from backend.models.parser_review import ParserReviewQueue
from backend.models.scraper_run import ScraperRun
from backend.models.ticker import Ticker
from backend.models.financial import FinancialPeriod
from backend.services.market import get_data_health

router = APIRouter(tags=["admin"])


class ParserReviewItem(BaseModel):
    id: int
    source_type: str
    source_url: str
    symbol: str | None
    confidence: float | None
    status: str
    raw_excerpt: str | None
    created_at: datetime


class ParserReviewListResponse(BaseModel):
    items: list[ParserReviewItem]


class ParserReviewPatch(BaseModel):
    status: str
    reviewer_note: str | None = None


class ScraperHealthItem(BaseModel):
    scraper_name: str
    last_success_at: datetime | None
    last_run_at: datetime | None
    records_ingested: int
    error_message: str | None


class ScraperHealthResponse(BaseModel):
    scrapers: list[ScraperHealthItem]
    data_health: dict | None = None


def require_admin(x_admin_key: str | None = Header(None, alias="X-Admin-Key")) -> None:
    if not settings.admin_api_key or x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Admin access denied")


@router.get("/admin/scraper-health", response_model=ScraperHealthResponse)
async def scraper_health(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_admin),
) -> ScraperHealthResponse:
    rows = (
        await db.execute(
            select(ScraperRun).order_by(desc(ScraperRun.last_run_at)).limit(100)
        )
    ).scalars().all()
    seen: set[str] = set()
    scrapers: list[ScraperHealthItem] = []
    for row in rows:
        if row.scraper_name in seen:
            continue
        seen.add(row.scraper_name)
        scrapers.append(
            ScraperHealthItem(
                scraper_name=row.scraper_name,
                last_success_at=row.last_success_at,
                last_run_at=row.last_run_at,
                records_ingested=row.records_ingested,
                error_message=row.error_message,
            )
        )
    health = await get_data_health(db)
    return ScraperHealthResponse(
        scrapers=scrapers,
        data_health=health.model_dump() if health else None,
    )


@router.get("/admin/parser-review", response_model=ParserReviewListResponse)
async def parser_review_list(
    status: str = Query("pending"),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_admin),
) -> ParserReviewListResponse:
    rows = (
        await db.execute(
            select(ParserReviewQueue)
            .where(ParserReviewQueue.status == status)
            .order_by(desc(ParserReviewQueue.created_at))
            .limit(50)
        )
    ).scalars().all()
    items = [
        ParserReviewItem(
            id=r.id,
            source_type=r.source_type,
            source_url=r.source_url,
            symbol=r.symbol,
            confidence=float(r.confidence) if r.confidence else None,
            status=r.status,
            raw_excerpt=r.raw_excerpt,
            created_at=r.created_at,
        )
        for r in rows
    ]
    return ParserReviewListResponse(items=items)


@router.patch("/admin/parser-review/{review_id}")
async def parser_review_patch(
    review_id: int,
    body: ParserReviewPatch,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_admin),
) -> dict:
    if body.status not in ("approved", "rejected", "pending"):
        raise HTTPException(status_code=400, detail="Invalid status")
    row = await db.get(ParserReviewQueue, review_id)
    if not row:
        raise HTTPException(status_code=404, detail="Review item not found")
    row.status = body.status
    row.reviewer_note = body.reviewer_note
    row.reviewed_at = datetime.now(UTC)
    await db.commit()
    return {"id": review_id, "status": body.status}


class FailedTaskItem(BaseModel):
    id: int
    task_id: str
    task_name: str
    error_message: str | None
    failed_at: datetime
    retried: bool


class FailedTaskListResponse(BaseModel):
    items: list[FailedTaskItem]


class DataQualityReport(BaseModel):
    stale_scrapers: list[str]
    stale_index_symbols: list[str] = []
    tickers_missing_financials: int
    total_tickers: int
    scraper_health: dict | None = None


@router.get("/admin/failed-tasks", response_model=FailedTaskListResponse)
async def failed_tasks(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_admin),
) -> FailedTaskListResponse:
    rows = (
        await db.execute(
            select(FailedCeleryTask).order_by(desc(FailedCeleryTask.failed_at)).limit(100)
        )
    ).scalars().all()
    return FailedTaskListResponse(
        items=[
            FailedTaskItem(
                id=r.id,
                task_id=r.task_id,
                task_name=r.task_name,
                error_message=r.error_message,
                failed_at=r.failed_at,
                retried=r.retried,
            )
            for r in rows
        ]
    )


@router.get("/admin/data-quality", response_model=DataQualityReport)
async def data_quality(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_admin),
) -> DataQualityReport:
    from datetime import UTC, datetime, timedelta

    health = await get_data_health(db)
    stale = []
    cutoff = datetime.now(UTC) - timedelta(hours=24)
    for s in health.scrapers:
        if s.last_success_at is None or s.last_success_at < cutoff:
            stale.append(s.scraper_name)
    total = await db.scalar(select(func.count()).select_from(Ticker).where(Ticker.is_active.is_(True))) or 0
    with_fin = await db.scalar(
        select(func.count(func.distinct(FinancialPeriod.symbol)))
    ) or 0
    return DataQualityReport(
        stale_scrapers=stale,
        stale_index_symbols=health.stale_index_symbols,
        tickers_missing_financials=max(0, total - with_fin),
        total_tickers=total,
        scraper_health=health.model_dump(),
    )
