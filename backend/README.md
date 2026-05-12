# DiscountHub Backend

FastAPI backend for DiscountHub. The backend stores deal metadata, manages feed providers, syncs official marketplace/affiliate feeds, and tracks outbound deal clicks.

DiscountHub is an aggregator, not a marketplace: checkout, delivery, returns, and stock are controlled by the original marketplace.

## Current backend features

- FastAPI API server;
- SQLite storage for deals, feed providers, sync history, and click events;
- public deal endpoints for the Flutter app;
- admin API protected by `X-Admin-Token` or `?token=`;
- local admin panel for development;
- automatic feed provider registration from `config/feed_providers.json`;
- feed sync scheduler;
- eBay Browse API adapter;
- universal feed adapters: DiscountHub JSON, generic JSON, Google Merchant style JSON, Awin, Admitad, Rakuten, CJ, Impact, CSV;
- production safety checks for admin token, CORS, API docs, and admin panel.

## Local run on Windows PowerShell

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open locally:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/admin-panel?token=dev-local-admin-token
```

## Useful public endpoints

```text
GET /health
GET /deals
GET /deals?q=headphones&page_size=20&sort=newest
GET /deals/{deal_id}
GET /deals/{deal_id}/click
GET /clicks/summary
GET /categories
GET /marketplaces
GET /settings/rates
GET /storage/status
GET /security/status
```

## Useful admin endpoints

```text
GET    /admin/deals
POST   /admin/deals
POST   /admin/deals/import
GET    /admin/deals/export
GET    /admin/feed-providers
POST   /admin/feed-providers
POST   /admin/feed-providers/{provider_id}/sync
POST   /admin/feed-providers/sync-all
GET    /admin/feed-providers/scheduler/status
POST   /admin/feed-providers/scheduler/run-once
```

Send the token either as a header:

```powershell
-H @{ "X-Admin-Token" = "dev-local-admin-token" }
```

or as a local testing query parameter:

```text
?token=dev-local-admin-token
```

## eBay Browse API

Local `.env` needs:

```env
EBAY_CLIENT_ID=...
EBAY_CLIENT_SECRET=...
EBAY_DEFAULT_MARKETPLACE_ID=EBAY_US
EBAY_REFERENCE_ID=discounthub
EBAY_CAMPAIGN_ID=
```

`EBAY_CAMPAIGN_ID` may be empty during data testing. Fill it when the eBay Partner Network campaign is ready so outgoing links can become monetized affiliate links.

## Stage 48 cleanup

Run after applying the Stage 48 patch:

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend
.\.venv\Scripts\Activate.ps1
python .\scripts\stage48_mvp_cleanup.py
```

The script creates a database backup before changing anything.

## Production notes

Use `.env.production.example` as the production template. For production:

- set `ENVIRONMENT=production`;
- use a long random `ADMIN_API_TOKEN`;
- set real `CORS_ORIGINS`;
- keep `ADMIN_PANEL_ENABLED=false`;
- keep `DOCS_ENABLED=false` and `OPENAPI_ENABLED=false`;
- store the SQLite database on a persistent volume;
- do not deploy local `.env`, `.venv`, or `backend/data/*.sqlite3` from your desktop ZIP.
