from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database import close_redis
from backend.middleware.rate_limit import RateLimitMiddleware
from backend.routes import (
    admin,
    alerts,
    api_keys,
    compare,
    context,
    fundamentals,
    governance,
    health,
    intelligence,
    notification_prefs,
    notifications,
    overview,
    portfolio,
    screener,
    smart_money,
    tickers,
    webhooks,
    watchlist,
    websocket_prices,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_redis()


app = FastAPI(
    title="PSX Intelligence Platform API",
    version="1.0.0",
    lifespan=lifespan,
)

if settings.sentry_dsn:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(dsn=settings.sentry_dsn, integrations=[FastApiIntegration()])
    except ImportError:
        pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)

app.include_router(health.router)
app.include_router(tickers.router)
app.include_router(fundamentals.router)
app.include_router(governance.router)
app.include_router(overview.router)
app.include_router(context.router)
app.include_router(compare.router)
app.include_router(intelligence.router)
app.include_router(screener.router)
app.include_router(watchlist.router)
app.include_router(alerts.router)
app.include_router(notifications.router)
app.include_router(notification_prefs.router)
app.include_router(portfolio.router)
app.include_router(smart_money.router)
app.include_router(api_keys.router)
app.include_router(webhooks.router)
app.include_router(admin.router)
app.include_router(websocket_prices.router)
