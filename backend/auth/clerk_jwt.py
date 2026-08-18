"""Clerk JWT verification via JWKS."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx
import jwt
from jwt import PyJWKClient

from backend.config import settings

logger = logging.getLogger(__name__)

_jwk_client: PyJWKClient | None = None


@dataclass
class ClerkTokenPayload:
    user_id: str
    email: str | None = None


def _get_jwk_client() -> PyJWKClient | None:
    global _jwk_client
    if not settings.clerk_jwks_url:
        return None
    if _jwk_client is None:
        _jwk_client = PyJWKClient(settings.clerk_jwks_url, cache_keys=True)
    return _jwk_client


def verify_clerk_token(token: str) -> ClerkTokenPayload | None:
    if not settings.clerk_jwks_url:
        return None
    try:
        client = _get_jwk_client()
        if not client:
            return None
        signing_key = client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        user_id = payload.get("sub")
        if not user_id:
            return None
        email = payload.get("email") or payload.get("primary_email_address")
        return ClerkTokenPayload(user_id=user_id, email=email)
    except Exception as exc:
        logger.debug("JWT verification failed: %s", exc)
        return None


def update_clerk_plan_metadata(user_id: str, plan_tier: str) -> None:
    """Sync plan tier to Clerk public metadata (best-effort)."""
    if not settings.clerk_secret_key:
        return
    try:
        with httpx.Client(timeout=10.0) as client:
            client.patch(
                f"https://api.clerk.com/v1/users/{user_id}/metadata",
                headers={
                    "Authorization": f"Bearer {settings.clerk_secret_key}",
                    "Content-Type": "application/json",
                },
                json={"public_metadata": {"plan": plan_tier}},
            )
    except Exception as exc:
        logger.warning("Failed to update Clerk metadata: %s", exc)
