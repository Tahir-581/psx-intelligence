import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user_optional, require_pro_user
from backend.database import get_db, get_redis
from backend.models.user import User
from backend.schemas.screener import (
    ScreenerPresetCreate,
    ScreenerPresetItem,
    ScreenerPresetListResponse,
    ScreenerRequest,
    ScreenerResponse,
)
from backend.services.screener import (
    create_preset,
    delete_preset,
    list_presets,
    run_screener,
    screener_results_to_csv,
)

router = APIRouter(tags=["screener"])


@router.post("/screener", response_model=ScreenerResponse)
async def screen_stocks(
    body: ScreenerRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    user: User | None = Depends(get_current_user_optional),
) -> ScreenerResponse:
    return await run_screener(db, redis, body, user)


@router.get("/screener/presets", response_model=ScreenerPresetListResponse)
async def get_screener_presets(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_pro_user),
) -> ScreenerPresetListResponse:
    return await list_presets(db, user)


@router.post("/screener/presets", response_model=ScreenerPresetItem)
async def save_screener_preset(
    body: ScreenerPresetCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_pro_user),
) -> ScreenerPresetItem:
    return await create_preset(db, user, body)


@router.delete("/screener/presets/{preset_id}", status_code=204)
async def remove_screener_preset(
    preset_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_pro_user),
) -> None:
    await delete_preset(db, user, preset_id)


@router.post("/screener/export")
async def export_screener_csv(
    body: ScreenerRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    user: User = Depends(require_pro_user),
) -> StreamingResponse:
    export_body = body.model_copy(update={"page": 1, "page_size": 5000})
    result = await run_screener(db, redis, export_body, user)
    csv_text = screener_results_to_csv(result.items)
    return StreamingResponse(
        io.StringIO(csv_text),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=screener_results.csv"},
    )
