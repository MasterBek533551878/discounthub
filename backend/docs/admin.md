# DiscountHub Admin API

Stage 16 adds protected admin endpoints for managing deals in the local SQLite database.

## Admin token

Default local token:

```text
dev-local-admin-token
```

You can change it in `.env`:

```env
ADMIN_API_TOKEN=your-secret-token
```

Admin endpoints accept the token in either:

```http
X-Admin-Token: dev-local-admin-token
```

or, for quick Swagger/browser testing:

```text
?token=dev-local-admin-token
```

## Endpoints

```text
GET    /admin/deals
GET    /admin/deals/{deal_id}
POST   /admin/deals
POST   /admin/deals/bulk
DELETE /admin/deals/{deal_id}
POST   /admin/deals/reset-demo
```

## Add or update one deal

PowerShell example:

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend
$body = Get-Content .\examples\admin_deal_payload.json -Raw
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/admin/deals" `
  -Headers @{ "X-Admin-Token" = "dev-local-admin-token" } `
  -ContentType "application/json" `
  -Body $body
```

## Reset database to demo deals

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/admin/deals/reset-demo" `
  -Headers @{ "X-Admin-Token" = "dev-local-admin-token" }
```

## Why this matters

This is the bridge between the MVP and real marketplace ingestion. Later, marketplace importers can upsert normalized deals into the same repository without changing the mobile app.
