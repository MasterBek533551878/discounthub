# DiscountHub production security

Stage 28 adds a small production safety layer so the backend does not accidentally launch with local development defaults.

## New environment variables

```env
ENVIRONMENT=production
ENFORCE_PRODUCTION_SAFETY=true
ADMIN_API_TOKEN=replace-with-long-random-token-at-least-32-chars
ADMIN_PANEL_ENABLED=false
DOCS_ENABLED=false
OPENAPI_ENABLED=false
CORS_ORIGINS=https://your-app-domain.example
```

## What is blocked in strict production

When `ENVIRONMENT=production` and `ENFORCE_PRODUCTION_SAFETY=true`, the backend refuses to start if:

- `ADMIN_API_TOKEN` is missing;
- `ADMIN_API_TOKEN` is still `dev-local-admin-token`;
- `ADMIN_API_TOKEN` is too short;
- `CORS_ORIGINS=*`;
- `ADMIN_PANEL_ENABLED=true`;
- `DOCS_ENABLED=true` or `OPENAPI_ENABLED=true`.

This is intentional. Local development can still use `ENVIRONMENT=development` or `production-local`.

## Security status endpoint

```text
GET /security/status
```

It returns safe metadata about the current configuration. It does not expose the admin token.

## Local production-like test without Docker

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend
.\.venv\Scripts\Activate.ps1
.\scripts\production_start_local.ps1
```

In another PowerShell:

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend
.\.venv\Scripts\Activate.ps1
.\scripts\production_health_check.ps1 -BaseUrl http://127.0.0.1:8000 -AdminToken dev-local-admin-token
.\scripts\production_config_check.ps1 -BaseUrl http://127.0.0.1:8000
```

## Generate a real admin token

```powershell
.\scripts\make_admin_token.ps1
```
