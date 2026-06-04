param(
  [string]$ApiBaseUrl = 'https://api.discounthub.uz'
)

$ErrorActionPreference = 'Stop'

Write-Host '== DiscountHub Stage 79: Delivery region API check ==' -ForegroundColor Cyan
Write-Host "API: $ApiBaseUrl"

$health = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/health" -TimeoutSec 20
Write-Host "Backend health: $($health.status) ($($health.environment))" -ForegroundColor Green

$facets = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals/facets" -TimeoutSec 60
Write-Host "Total deals: $($facets.total)"
Write-Host 'Delivery regions:' -ForegroundColor Yellow
$facets.deliveryRegions | Format-Table id,name,count -AutoSize

foreach ($region in @('global', 'cis', 'europe', 'usa', 'latam')) {
  $resp = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals?delivery_region=$region&page_size=3&sort=newest" -TimeoutSec 60
  Write-Host "delivery_region=$region total=$($resp.total) returned=$($resp.items.Count)"
  if ($resp.items.Count -gt 0) {
    $resp.items | Select-Object -First 1 id,title,platform,deliveryRegions | Format-List
  }
}

Write-Host 'Stage 79 delivery-region check completed.' -ForegroundColor Green
