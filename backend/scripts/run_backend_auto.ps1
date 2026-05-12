Set-Location $PSScriptRoot\..

if (-not (Test-Path ".venv\Scripts\Activate.ps1")) {
  Write-Host "Virtual environment not found. Create it first:" -ForegroundColor Yellow
  Write-Host "py -m venv .venv"
  exit 1
}

& .\.venv\Scripts\Activate.ps1

Write-Host "Starting DiscountHub backend in automatic feed mode..." -ForegroundColor Green
Write-Host "Configured providers are loaded from: backend/config/feed_providers.json" -ForegroundColor Cyan
Write-Host "Scheduler is enabled by default and runs on startup." -ForegroundColor Cyan

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
