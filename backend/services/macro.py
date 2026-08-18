from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.macro_series import MacroSeries
from backend.schemas.context import MacroPoint, MacroSeriesResponse


async def get_macro_series(
    db: AsyncSession,
    series_code: str,
    *,
    from_dt: datetime | None = None,
    to_dt: datetime | None = None,
) -> MacroSeriesResponse:
    query = select(MacroSeries).where(MacroSeries.series_code == series_code)
    if from_dt:
        query = query.where(MacroSeries.time >= from_dt)
    if to_dt:
        query = query.where(MacroSeries.time <= to_dt)
    result = await db.execute(query.order_by(MacroSeries.time.asc()))
    points = [
        MacroPoint(
            time=row.time,
            value=float(row.value),
            unit=row.unit,
        )
        for row in result.scalars().all()
    ]
    return MacroSeriesResponse(series_code=series_code, points=points)
