# Deployment

## Railway (API + workers + DB + Redis)

1. Create a Railway project with services: `api`, `celery-worker`, `celery-beat`, TimescaleDB, Redis.
2. Set environment variables from `.env.example` on each Python service.
3. Deploy using `docker/Dockerfile.api` (see `railway.toml`).
4. Run migrations on deploy: `alembic upgrade head`.
5. Expose the API service HTTPS URL as `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_WS_URL` (wss://) on Vercel.

## Vercel (frontend)

1. Import the repo with root directory `frontend`.
2. Set `NEXT_PUBLIC_API_URL` to the Railway API URL.
3. Set `NEXT_PUBLIC_WS_URL` to `wss://<railway-api-host>` (WebSocket bypasses Next.js rewrites).
4. Deploy — preview builds run on every PR via GitHub Actions + Vercel integration.

## Post-deploy data bootstrap

```bash
railway run python scripts/seed_tickers.py
railway run python scripts/backfill_prices.py --limit 50
```
