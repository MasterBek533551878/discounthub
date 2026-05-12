# DiscountHub feed providers

Stage 20 adds a small feed provider registry to the local backend.

The goal is to move from one-off URL imports to reusable feed sources. This is the base for future scheduled sync jobs.

## Admin endpoints

All endpoints require:

```http
X-Admin-Token: dev-local-admin-token
```

### List providers

```http
GET /admin/feed-providers
```

### Create or update provider

```http
POST /admin/feed-providers
```

Example body:

```json
{
  "id": "demo_feed",
  "name": "Demo provider feed",
  "url": "http://127.0.0.1:9000/provider_feed.json",
  "enabled": true,
  "replaceOnSync": false
}
```

### Sync one provider

```http
POST /admin/feed-providers/demo_feed/sync
```

### Sync all enabled providers

```http
POST /admin/feed-providers/sync-all
```

### Delete provider

```http
DELETE /admin/feed-providers/demo_feed
```

## Local test

Terminal 1: run backend.

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Terminal 2: serve example feed.

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend\examples
python -m http.server 9000
```

Terminal 3: add and sync provider.

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend
.\scripts\add_feed_provider.ps1
.\scripts\sync_feed_provider.ps1 -ProviderId demo_feed
```

Or sync all enabled providers:

```powershell
.\scripts\sync_all_feed_providers.ps1
```

## Admin panel

Open:

```text
http://127.0.0.1:8000/admin-panel
```

Use the new blocks:

- **Feed URL import** for one-off import by URL.
- **Feed providers** for saved reusable feed sources.

## Production note

This is still MVP/local admin. Production needs real authentication, audit logs, provider-specific adapters, retry limits, and scheduler integration.
