# PSX Intelligence Platform

A market-data and research platform for the Pakistan Stock Exchange (PSX), with a US "smart money" module built on SEC 13F and Form 4 filings. It scrapes and normalizes prices, announcements, financial-statement PDFs, news, macro series and social posts. It stores them in TimescaleDB, enriches them with NLP (FinBERT sentiment, topic tagging, entity linking, significance scoring and Anthropic-API summaries), and serves everything through a FastAPI API and a Next.js dashboard.

## Highlights

- **Ingestion:** PSX symbols, EOD prices, live LTP, announcements and PDF financials/insider/ownership parsers; news RSS; SBP macro data; Twitter/Reddit/Telegram; SEC EDGAR 13F, delta and Form 4. Scheduled with Celery Beat and monitored in Flower.
- **Storage:** PostgreSQL + TimescaleDB hypertables, with Alembic migrations.
- **API:** FastAPI REST and WebSocket live prices covering snapshots, fundamentals and ratios, screener, alerts, portfolio, watchlists, notifications, webhooks and API keys, with rate limiting.
- **SaaS layer:** Clerk JWT auth, Free/Pro entitlements, and Stripe or LemonSqueezy billing.
- **Frontend:** Next.js, TanStack Query and lightweight-charts.
- **Tests:** pytest unit and integration tests, plus GitHub Actions CI.

**Stack:** Python · FastAPI · SQLAlchemy · Alembic · PostgreSQL/TimescaleDB · Redis · Celery · Hugging Face (FinBERT) · Anthropic API · Next.js · Clerk · Stripe · Docker · Railway

## Quick start (Docker)

**Windows:** If `docker` is not recognized, Docker Desktop is likely installed but not on PATH. Use:

```powershell
.\scripts\docker.ps1 compose up --build
```

Or add `C:\Program Files\Docker\Docker\resources\bin` to your system PATH, then restart the terminal.

```bash
cp .env.example .env
docker compose up --build
```

Services:
- API: http://localhost:8000/docs
- Flower: http://localhost:5555
- TimescaleDB: localhost:5432
- Redis: localhost:6379

## Initial data load

```bash
docker compose exec api python scripts/seed_tickers.py
docker compose exec api python scripts/backfill_prices.py --limit 20
docker compose exec api celery -A backend.celery_app call scrapers.tasks.scrape_eod_prices
```

## Local development (without Docker)

```bash
pip install -e ".[dev]"
alembic upgrade head
uvicorn backend.main:app --reload
```

Frontend:
```bash
cd frontend && npm install && npm run dev
```

## US Smart Money (SEC 13F)

Track US institutional investors, hedge funds, and SEC Form 4 insiders alongside PSX data.

```bash
alembic upgrade head
python -m scripts.ingest_sec_13f      # ~30 min, downloads ~80MB SEC ZIP
python -m scripts.ingest_sec_tickers
python -m scripts.ingest_sec_delta
python -m scripts.ingest_sec_form4
```

Set `SEC_USER_AGENT` in `.env` (required by SEC fair-access policy).

Frontend routes:
- `/smart-money/feed` — Live SEC filing feed
- `/smart-money/investors` — 13F filer directory (hedge fund filter)
- `/smart-money/investor/[cik]` — Investor profile and holdings
- `/smart-money/investments` — QoQ position changes
- `/smart-money/sec-insiders` — SEC Form 4 insider trades
- `/smart-money/alerts` — Browser-local SEC alerts

Without ingestion, the API returns mock data so the UI is testable immediately.

Quarterly ingest also runs via GitHub Actions (`.github/workflows/ingest-sec-13f.yml`) and Celery beat.

## Architecture

- `scrapers/` — PSX ingestion (symbols JSON API, EOD timeseries, market-watch LTP)
- `backend/` — FastAPI read API + WebSocket live prices
- `frontend/` — Next.js dashboard shell
- `migrations/` — Alembic + TimescaleDB hypertables

## Phase 1 endpoints

- `GET /tickers`
- `GET /ticker/{symbol}/snapshot`
- `GET /ticker/{symbol}/prices`
- `GET /market/summary`
- `GET /health/data`
- `WS /ws/prices/{symbol}`

## Phase 2 endpoints

- `GET /ticker/{symbol}/announcements?category=&page=`
- `GET /ticker/{symbol}/financials?period_type=quarterly|annual`
- `GET /ticker/{symbol}/ratios`
- `GET /ticker/{symbol}/insider-trades?days=90`
- `GET /ticker/{symbol}/ownership`

Snapshot (`GET /ticker/{symbol}/snapshot`) now includes P/E TTM, EPS TTM, dividend yield, and free float % when available.

## Phase 2 bootstrap

```bash
docker compose exec api alembic upgrade head
docker compose exec api python scripts/backfill_announcements.py --limit 10
docker compose exec api python scripts/seed_phase2_sample.py
```

Celery Beat schedules announcements scrape (every 15 min on market days), PDF parsing (hourly), and ratio recomputation (17:00 PKT weekdays).

## Phase 3 endpoints

- `GET /ticker/{symbol}/news?source=&topic=&page=`
- `GET /ticker/{symbol}/corporate-actions`
- `GET /ticker/{symbol}/events?min_significance=`
- `GET /ticker/{symbol}/beta`
- `GET /macro/{series_code}?from=&to=`
- `GET /market/sectors?range=1d|1w|1m|ytd`
- `GET /market/corporate-calendar?from=&to=`

Extended:
- `GET /ticker/{symbol}/prices?overlay=KSE100` — normalized KSE-100 comparison series
- `GET /ticker/{symbol}/snapshot` — adds `beta`, `sector_return_1m`, `next_dividend_ex_date`

## Phase 3 bootstrap

```bash
docker compose exec api alembic upgrade head
docker compose exec api python scripts/backfill_corporate_actions.py
docker compose exec api python scripts/backfill_news.py --days 30 --limit-sources business_recorder,dawn
docker compose exec api python scripts/seed_macro.py
docker compose exec api python scripts/seed_phase3_sample.py
```

Celery Beat adds: news RSS (30 min), Profit/press scrape (2h), macro daily 18:00 PKT, sector stats 17:30 PKT, corporate action + material event extractors.

## Phase 4 endpoints

- `GET /ticker/{symbol}/sentiment?days=90` (Pro)
- `GET /ticker/{symbol}/summary` (Pro)
- `GET /ticker/{symbol}/social?days=30` (Pro)
- `GET /watchlist` (auth)
- `POST /watchlist/{symbol}` (auth)
- `DELETE /watchlist/{symbol}` (auth)
- `POST /billing/create-checkout-session` (auth)
- `GET /billing/portal` (auth)
- `POST /billing/webhook` (Stripe)
- `GET /admin/scraper-health` (admin key)
- `GET /admin/parser-review` (admin key)
- `PATCH /admin/parser-review/{id}` (admin key)

Extended:
- `GET /ticker/{symbol}/news` — adds `ai_summary`, `sentiment_badge` for Pro; 30-day cutoff for Free
- `GET /ticker/{symbol}/financials` — last 4 quarters for Free, full history for Pro

## Phase 4 bootstrap

1. Create accounts: [Clerk](https://clerk.com), [Stripe](https://stripe.com) (or LemonSqueezy for PK cards), [Twitter Developer](https://developer.twitter.com), [Anthropic](https://anthropic.com), [HuggingFace](https://huggingface.co).

2. Copy env vars from `.env.example` into `.env` (never commit secrets).

3. Run migration and seed:

```bash
docker compose exec api alembic upgrade head
docker compose exec api python scripts/backfill_social.py --source twitter --days 7 --limit-symbols 20
```

4. Frontend: set `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` and install deps:

```bash
cd frontend && npm install && npm run dev
```

### Pakistan payments note

Stripe does not support Pakistani-issued cards directly. Options:
- Use LemonSqueezy as Merchant of Record (swap `BillingProvider` implementation)
- Foreign/Wise virtual card for business Stripe account

### Celery Beat (Phase 4)

- Twitter scrape: every 2h on market days
- Sentiment aggregate: daily 23:00 PKT
- News summarization: hourly `:15` on market days
- Weekly company summaries: Sunday 03:00 PKT

## Phase 5 endpoints

- `POST /screener` — dynamic multi-filter stock screener (Free: 3 filter groups; Pro: unlimited)
- `GET /screener/presets` (Pro)
- `POST /screener/presets` (Pro)
- `DELETE /screener/presets/{id}` (Pro)
- `POST /screener/export` (Pro) — CSV download
- `GET /alerts` (Pro)
- `POST /alerts` (Pro)
- `PATCH /alerts/{id}` (Pro)
- `DELETE /alerts/{id}` (Pro)
- `GET /alerts/events` (Pro)
- `GET /notifications` (auth)
- `PATCH /notifications/{id}/read` (auth)
- `POST /notifications/read-all` (auth)
- `GET /portfolio` (Pro)
- `POST /portfolio/holdings` (Pro)
- `PATCH /portfolio/holdings/{id}` (Pro)
- `DELETE /portfolio/holdings/{id}` (Pro)
- `GET /portfolio/transactions` (Pro)
- `GET /portfolio/export` (Pro)
- `GET /compare?symbols=ENGRO,LUCK` — Free: 2 symbols; Pro: 4
- `GET /ticker/{symbol}/peers`
- `POST /api-keys` (Pro)
- `GET /api-keys` (Pro)
- `DELETE /api-keys/{id}` (Pro)

Pro API access: pass `X-API-Key: psx_live_...` header on GET endpoints (300 req/min per key).

## Phase 5 bootstrap

```bash
docker compose exec api alembic upgrade head
docker compose exec api python scripts/seed_index_constituents.py
docker compose exec api python scripts/seed_phase5_demo.py  # set DEMO_PRO_USER_ID to your Clerk user id
```

### Celery Beat (Phase 5)

- `evaluate_alerts`: every 5 min during market hours (09:30–15:30 PKT); every 30 min off-hours

## Master completion (v1.0)

Run migrations 006–007 after Phase 5:

```bash
docker compose exec api alembic upgrade head
docker compose exec api python scripts/seed_governance_fallback.py
docker compose exec api python scripts/backfill_full.py --limit 50  # optional 5Y checkpoint backfill
```

### New endpoints

**Charts & market**
- `GET /ticker/{symbol}/prices?adjusted=true&overlays=SMA20,SMA50,SMA200,EMA12,EMA26,BB20&overlay=KSE100|SECTOR`
- `GET /ticker/{symbol}/chart-markers?from=&to=`
- Snapshot adds: `vwap`, `circuit_breaker`, `trading_halt`, `board_change_30d`

**Governance**
- `GET /ticker/{symbol}/governance`
- `GET /ticker/{symbol}/credit-ratings`

**Overview BFF**
- `GET /ticker/{symbol}/overview`

**Financials**
- `GET /ticker/{symbol}/financials/export` (Pro CSV)
- Financials response adds `validation_flags`, `yoy_change_pct`, `source_pdf_url` per period

**Corporate actions**
- `GET /ticker/{symbol}/corporate-actions/analytics` — DPS series, TERP

**News & sentiment**
- `GET /ticker/{symbol}/news/volume?days=90`
- `GET /ticker/{symbol}/news/keywords` (Pro)
- `GET /ticker/{symbol}/sentiment/price-overlay?days=90` (Pro)
- `POST /ticker/{symbol}/summary/refresh` (Pro, 1/24h per ticker)

**Notifications v2**
- `GET/PATCH /notifications/preferences`
- `POST /notifications/push-subscribe`

**Admin**
- `GET /admin/failed-tasks`
- `GET /admin/data-quality`

**Webhooks** (when `WEBHOOKS_ENABLED=true`, Pro+)
- `GET/POST /webhooks`

### Celery Beat (Master)

- `scrape_governance`: daily 03:30 PKT
- `send_daily_digest`: daily 08:00 PKT

### Feature flags & optional integrations

| Env var | Feature |
|---------|---------|
| `BILLING_PROVIDER=lemonsqueezy` | PK-friendly billing |
| `PSX_INTRADAY_API_KEY` | Licensed intraday OHLCV module (inactive without key) |
| `WEBHOOKS_ENABLED` | Signed alert webhooks |
| `B2_*` | Raw HTML/PDF archive on scrape |
| `SENTRY_DSN` / `NEXT_PUBLIC_SENTRY_DSN` | Error monitoring |
| `VAPID_*` / `NEXT_PUBLIC_VAPID_PUBLIC_KEY` | Browser push |
| `TWILIO_*` | WhatsApp alerts |
| `TELEGRAM_BOT_TOKEN` / `REDDIT_*` | Social scrapers |

### SECP note

If SECP scraping is auth-blocked, governance data is populated from PSX announcements + `data/governance_seed.csv` fallback. Document any remaining gap in production deployment notes.

### Smoke test

```bash
docker compose exec api python scripts/smoke_platform.py
pytest tests/ -q
cd frontend && npm run lint && npm run typecheck
```

Manual checks:
1. Home: KSE-100, heatmap, movers, corporate calendar
2. `/ticker/ENGRO` — all tabs (Overview, Chart, Financials, Governance, Corp Actions, News, Sentiment, Social, Peers)
3. Chart: overlays, adjusted prices, event markers
4. `/screener` — filter + presets (Pro)
5. `/notifications` — preferences page
6. `/docs` — OpenAPI complete

## Production readiness

- [x] Migrations 001–007 (governance, notifications, webhooks)
- [x] Celery Beat: governance scrape + daily digest + all Phase 1–5 jobs
- [x] Optional integrations env-gated (B2, Sentry, Twilio, intraday, webhooks)
- [x] PWA manifest + service worker
- [ ] SendGrid domain verified (`SENDGRID_API_KEY`, `ALERTS_FROM_EMAIL`)
- [ ] Stripe or LemonSqueezy webhooks live
- [ ] Clerk production instance configured
- [ ] DB backups configured
- [ ] Sentry DSN set in production


## License

MIT
