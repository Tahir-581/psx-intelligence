from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.services import sec_filers as svc
from scrapers.sec.edgar import (
    filter_mock_investors,
    get_mock_investor_profile,
    get_recent_filings,
)

router = APIRouter(prefix="/smart-money", tags=["smart-money"])

CACHE_HEADERS = {"Cache-Control": "s-maxage=60, stale-while-revalidate=300"}


@router.get("/investors")
async def list_investors(
    type: str = Query("all", alias="type"),
    q: str | None = None,
    sort: str = Query("aum"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if await svc.has_filer_data(db):
        return await svc.query_investors(
            db, q=q, investor_type=type, sort=sort, page=page, limit=limit
        )

    investors = filter_mock_investors(type if type != "all" else None, q)
    return {
        "investors": investors,
        "total": len(investors),
        "page": 1,
        "limit": len(investors),
        "totalAum": sum(i["aum"] for i in investors),
    }


@router.get("/investor/{cik}")
async def get_investor(cik: str, db: AsyncSession = Depends(get_db)) -> dict:
    if await svc.has_filer_data(db):
        profile = await svc.query_investor_profile(db, cik)
        if profile:
            return profile

    mock = get_mock_investor_profile(cik)
    if mock:
        return mock
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Investor not found")


@router.get("/investor/{cik}/holdings")
async def get_investor_holdings(
    cik: str,
    period: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    sort: str = Query("value"),
    order: str = Query("desc"),
    q: str | None = None,
    changes: bool = Query(False),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if await svc.has_filer_data(db):
        return await svc.query_holdings(
            db,
            cik=cik,
            period=period,
            page=page,
            limit=limit,
            sort=sort,
            order=order,
            q=q,
            changes_only=changes,
        )

    mock = get_mock_investor_profile(cik)
    holdings = mock.get("holdings", []) if mock else []
    return {
        "holdings": holdings,
        "total": len(holdings),
        "page": 1,
        "limit": len(holdings),
        "reportPeriod": "2026-03-31",
        "periods": ["2026-03-31"],
        "summary": {
            "totalValue": mock["aum"] if mock else 0,
            "holdingsCount": len(holdings),
            "top5Concentration": mock.get("top5Concentration", 0) if mock else 0,
        },
    }


@router.get("/investments")
async def list_investments(
    action: str = Query("all"),
    sector: str = Query("all"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if await svc.has_filer_data(db):
        return await svc.query_investment_changes(
            db, action=action if action != "all" else None, sector=sector, page=page, limit=limit
        )

    items = svc.get_mock_investments(action if action != "all" else None, sector)
    return {
        "investments": items,
        "total": len(items),
        "page": 1,
        "limit": len(items),
    }


@router.get("/filings")
async def list_filings(
    form: str = Query("all"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    form_types = None
    if form == "13F":
        form_types = ["13F"]
    elif form == "4":
        form_types = ["4"]
    elif form in ("13D", "13DG"):
        form_types = ["13D", "13G"]

    filings = await get_recent_filings(form_types)
    if await svc.has_filer_data(db):
        for filing in filings:
            if filing.get("investorCik"):
                continue
            name = filing.get("investorName", "")
            if name:
                cik = await svc.query_filer_cik_by_name(db, name)
                if cik:
                    filing["investorCik"] = cik

    return {"filings": filings}


@router.get("/sec-insiders")
async def list_sec_insiders(
    q: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await svc.query_sec_insiders(db, q=q, page=page, limit=limit)
