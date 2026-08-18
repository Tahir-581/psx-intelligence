"""Redis sliding-window rate limiting middleware."""

from __future__ import annotations

import time

import redis
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from backend.auth.entitlements import rate_limit_for
from backend.config import settings

SKIP_PATHS = {"/health", "/billing/webhook", "/openapi.json", "/docs", "/redoc"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        self._redis: redis.Redis | None = None

    def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(settings.redis_url, decode_responses=True)
        return self._redis

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in SKIP_PATHS:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        user_id: str | None = None
        plan_tier: str | None = None

        token = request.headers.get("Authorization", "")
        api_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")

        if api_key:
            limit = 300
            key_suffix = f"apikey:{api_key[:12]}"
        elif token.startswith("Bearer "):
            from backend.auth.clerk_jwt import verify_clerk_token

            payload = verify_clerk_token(token[7:].strip())
            if payload:
                user_id = payload.user_id
                try:
                    from sqlalchemy import create_engine, text

                    engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
                    with engine.connect() as conn:
                        row = conn.execute(
                            text("SELECT plan_tier FROM users WHERE id = :id"),
                            {"id": user_id},
                        ).fetchone()
                        if row:
                            plan_tier = row[0]
                except Exception:
                    pass
            limit, key_suffix = rate_limit_for(user_id=user_id, plan_tier=plan_tier)
        else:
            limit, key_suffix = rate_limit_for()
            key_suffix = f"ip:{client_ip}"
        window = int(time.time() // 60)
        redis_key = f"ratelimit:{key_suffix}:{window}"

        try:
            r = self._get_redis()
            count = r.incr(redis_key)
            if count == 1:
                r.expire(redis_key, 60)
            if count > limit:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded"},
                )
        except Exception:
            return await call_next(request)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        return response
