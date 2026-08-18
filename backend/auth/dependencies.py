"""FastAPI auth dependencies."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.clerk_jwt import ClerkTokenPayload, verify_clerk_token
from backend.auth.users import upsert_user
from backend.database import get_db
from backend.models.user import User


def _extract_bearer(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    return None


def _extract_api_key(request: Request) -> str | None:
    return request.headers.get("X-API-Key") or request.headers.get("x-api-key")


async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    api_key = _extract_api_key(request)
    if api_key:
        from backend.services.api_keys import authenticate_api_key

        return await authenticate_api_key(db, api_key)

    token = _extract_bearer(request)
    if not token:
        return None
    payload = verify_clerk_token(token)
    if not payload:
        return None
    return await upsert_user(db, payload.user_id, payload.email)


async def require_user(
    user: User | None = Depends(get_current_user_optional),
) -> User:
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


async def require_pro_user(
    user: User = Depends(require_user),
) -> User:
    return user
