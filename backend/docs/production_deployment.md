# DiscountHub production deployment

Stage 27 prepares the FastAPI backend for Docker/VPS/Render/Railway-style deployment.

## What changes in production

The app should not rely on manual product entry. Production data should come from configured feed providers:

```text
Official affiliate feeds / partner APIs
        ↓
Feed provider adapters
        ↓
Automatic scheduler
        ↓
SQLite/PostgreSQL-compatible repository later
        ↓
Flutter app API
```

The local admin panel remains only for development, emergency corrections, and monitoring.

## Important files

```text
backend/Dockerfile
backend/.dockerignore
backend/.env.production.example
backend/config/feed_providers.production.example.json
backend/render.yaml
backend/railway.toml
backend/docker-compose.yml
backend/scripts/docker_build.ps1
backend/scripts/docker_run_local.ps1
backend/scripts/production_health_check.ps1
backend/scripts/make_admin_token.ps1
```

## Required production environment variables

```text
ENVIRONMENT=production
DATABASE_PATH=/data/discounthub.sqlite3
ADMIN_API_TOKEN=<long random token>
AUTO_REGISTER_FEED_PROVIDERS=true
DEFAULT_FEED_PROVIDERS_PATH=config/feed_providers.production.example.json
FEED_SYNC_SCHEDULER_ENABLED=true
FEED_SYNC_RUN_ON_STARTUP=true
FEED_SYNC_INTERVAL_SECONDS=3600
FEED_SYNC_TIMEOUT_SECONDS=30
```

Generate a local admin token:

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend
.\scripts\make_admin_token.ps1
```

## Local Docker test

From `backend/`:

```powershell
.\scripts\docker_build.ps1
.\scripts\docker_run_local.ps1
```

Then open:

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/storage/status
http://127.0.0.1:8000/docs
```

Health check:

```powershell
.\scripts\production_health_check.ps1 -BaseUrl http://127.0.0.1:8000 -AdminToken dev-local-admin-token
```

## Docker Compose local test

From `backend/`:

```powershell
docker compose up --build
```

This stores SQLite data in a Docker volume named `discounthub_data`.

## Feed providers in production

`backend/config/feed_providers.production.example.json` is only a template. Replace it with real official provider URLs.

Example:

```json
{
  "providers": [
    {
      "id": "partner_001",
      "name": "Partner 001 official feed",
      "url": "https://partner.example.com/products.json",
      "adapter": "auto",
      "enabled": true,
      "replaceOnSync": false
    }
  ]
}
```

Supported adapters at this stage:

```text
auto
discounthub_json
generic_products
google_merchant
awin_products
```

## Notes

- Do not use the local demo feed URLs in production. `127.0.0.1:9000` exists only on your computer.
- Set a real `ADMIN_API_TOKEN` before deployment.
- Use persistent storage for SQLite. Without persistent storage, the database can reset after redeploys.
- Later, when traffic grows, migrate from SQLite to PostgreSQL.
