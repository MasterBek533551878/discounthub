$ErrorActionPreference = "Stop"

Write-Host "Starting DiscountHub backend locally without Docker..." -ForegroundColor Green
Write-Host "This is useful when Docker Desktop is not installed." -ForegroundColor Yellow
Write-Host "This uses production-local mode, not strict production safety mode." -ForegroundColor Yellow

$env:ENVIRONMENT = "production-local"
$env:ADMIN_API_TOKEN = "dev-local-admin-token"
$env:CORS_ORIGINS = "*"
$env:ADMIN_PANEL_ENABLED = "true"
$env:DOCS_ENABLED = "true"
$env:OPENAPI_ENABLED = "true"
$env:FEED_SYNC_SCHEDULER_ENABLED = "true"
$env:FEED_SYNC_RUN_ON_STARTUP = "true"
$env:DEFAULT_FEED_PROVIDERS_PATH = "config/feed_providers.json"
$env:HOST = "0.0.0.0"
$env:PORT = "8000"

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
