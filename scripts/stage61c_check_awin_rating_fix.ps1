param(
  [string]$ApiBaseUrl = "http://127.0.0.1:8000",
  [int]$MaxFeeds = 20,
  [int]$MaxItemsPerFeed = 1000,
  [int]$MinDiscountPercent = 1,
  [int]$TimeoutSeconds = 180
)

$ErrorActionPreference = "Stop"

Write-Host "== DiscountHub Stage 61c: Awin rating normalization check =="
Write-Host "API: $ApiBaseUrl"
Write-Host ""

$health = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/health" -TimeoutSec 10
Write-Host "Backend health: $($health.status) ($($health.service))"
Write-Host ""

& "$PSScriptRoot\stage60_awin_diagnose_and_sync.ps1" `
  -ApiBaseUrl $ApiBaseUrl `
  -MaxFeeds $MaxFeeds `
  -MaxItemsPerFeed $MaxItemsPerFeed `
  -MinDiscountPercent $MinDiscountPercent `
  -TimeoutSeconds $TimeoutSeconds

Write-Host ""
Write-Host "Quick affiliate verification:"
$facets = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals/facets" -TimeoutSec 30
$facets.monetizationModes | Format-Table id,count
