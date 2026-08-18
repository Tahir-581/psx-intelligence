from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import require_pro_user
from backend.database import get_db
from backend.models.user import User
from backend.schemas.api_keys import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyListResponse,
)
from backend.services.api_keys import create_api_key, list_api_keys, revoke_api_key

router = APIRouter(tags=["api-keys"])


@router.post("/api-keys", response_model=ApiKeyCreateResponse)
async def generate_api_key(
    body: ApiKeyCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_pro_user),
) -> ApiKeyCreateResponse:
    return await create_api_key(db, user, body.label)


@router.get("/api-keys", response_model=ApiKeyListResponse)
async def get_api_keys(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_pro_user),
) -> ApiKeyListResponse:
    return await list_api_keys(db, user)


@router.delete("/api-keys/{key_id}", status_code=204)
async def delete_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_pro_user),
) -> None:
    await revoke_api_key(db, user, key_id)
