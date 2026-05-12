# DiscountHub feed import

Stage 19 adds URL-based feed import for real marketplace/affiliate integrations.

## Why this exists

The app should not scrape Amazon/AliExpress/eBay pages directly. For production, use official APIs, affiliate product feeds, or partner networks. This importer gives us a clean format for those feeds.

## Admin endpoint

```http
POST /admin/deals/import-url
X-Admin-Token: dev-local-admin-token
Content-Type: application/json
```

Body:

```json
{
  "url": "http://127.0.0.1:9000/provider_feed.json",
  "replace": false,
  "timeoutSeconds": 20
}
```

Supported feed shapes:

```json
{ "items": [ ...deals ] }
```

```json
{ "deals": [ ...deals ] }
```

```json
{ "products": [ ...deals ] }
```

or a plain array:

```json
[ ...deals ]
```

## Local test

Terminal 1: run backend.

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Terminal 2: serve the example feed.

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend\examples
python -m http.server 9000
```

Terminal 3: import from URL.

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend
.\scripts\import_deals_from_url.ps1 -FeedUrl http://127.0.0.1:9000/provider_feed.json
```

After import, check:

```text
http://127.0.0.1:8000/storage/status
http://127.0.0.1:8000/deals
```

## Production note

This is an MVP importer. Before production, add:

- per-source credentials;
- source-specific normalizers;
- import logs;
- duplicate detection by platform/product URL;
- rate limits;
- background scheduler;
- audit logs for admin actions.
