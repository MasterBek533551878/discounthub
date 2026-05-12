# DiscountHub backend import/export

Stage 18 adds JSON backup/import tools for the local admin workflow.

## Endpoints

All endpoints require the `X-Admin-Token` header.

### Export deals

```http
GET /admin/deals/export
X-Admin-Token: dev-local-admin-token
```

Returns:

```json
{
  "status": "ok",
  "exportedAt": "2026-05-04T00:00:00Z",
  "total": 9,
  "items": []
}
```

### Import deals

```http
POST /admin/deals/import
X-Admin-Token: dev-local-admin-token
Content-Type: application/json
```

Merge/update existing deals:

```json
{
  "replace": false,
  "items": []
}
```

Replace the local database before import:

```json
{
  "replace": true,
  "items": []
}
```

## Admin panel

Open:

```text
http://127.0.0.1:8000/admin-panel
```

Use the **Import / export** block to download a JSON backup, paste JSON, import from file, or replace the database.
