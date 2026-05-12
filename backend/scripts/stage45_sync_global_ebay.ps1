param(
  [string]$BaseUrl = 'http://127.0.0.1:8000',
  [string]$AdminToken = 'dev-local-admin-token',
  [int]$TimeoutSeconds = 35
)

$ErrorActionPreference = 'Stop'

Write-Host 'DiscountHub Stage 45 - eBay global feed expansion' -ForegroundColor Cyan
Write-Host "Backend: $BaseUrl"

try {
  Invoke-RestMethod -Uri "$BaseUrl/health" -Method Get -TimeoutSec 5 | Out-Null
} catch {
  throw "Backend is not reachable at $BaseUrl. Start backend first: python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
}

Write-Host 'Cleaning existing imported eBay deals before global resync...' -ForegroundColor Yellow
& "$PSScriptRoot\cleanup_ebay_deals.ps1" -BaseUrl $BaseUrl -AdminToken $AdminToken

Write-Host 'Registering and syncing configured providers...' -ForegroundColor Yellow
& "$PSScriptRoot\provider_sync_from_config.ps1" -BaseUrl $BaseUrl -AdminToken $AdminToken -TimeoutSeconds $TimeoutSeconds -WaitSeconds 5

Write-Host 'Checking marketplaces...' -ForegroundColor Yellow
Invoke-RestMethod -Uri "$BaseUrl/marketplaces" -Method Get -TimeoutSec 10 | ConvertTo-Json -Depth 6

Write-Host 'Checking first global deals...' -ForegroundColor Yellow
Invoke-RestMethod -Uri "$BaseUrl/deals?page_size=10&sort=discount_desc" -Method Get -TimeoutSec 10 | ConvertTo-Json -Depth 6

Write-Host 'Stage 45 sync finished.' -ForegroundColor Green
