param(
  [string]$ApiBaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

Write-Host "== DiscountHub Stage 74: public marketplace facets check =="
Write-Host "API: $ApiBaseUrl"
Write-Host ""

$health = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/health" -TimeoutSec 15
Write-Host "Backend health: $($health.status) ($($health.service))"
Write-Host ""

$facets = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals/facets" -TimeoutSec 60
Write-Host "Total deals: $($facets.total)"
Write-Host "Marketplaces visible to customers:"
$facets.marketplaces | Select-Object id, name, count | Format-Table -AutoSize

Write-Host ""
Write-Host "Sample by public marketplace filter:"
foreach ($platform in @("AliExpress", "eBay")) {
  $encoded = [System.Uri]::EscapeDataString($platform)
  $page = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals?platform=$encoded&page_size=5&sort=discount_desc" -TimeoutSec 60
  Write-Host ""
  Write-Host "$platform total=$($page.total); returned=$($page.items.Count)"
  $page.items | Select-Object title, platform, currentPrice, discountPercent | Format-Table -AutoSize
}

Write-Host ""
Write-Host "Stage 74 check completed. Expected customer-facing marketplaces: AliExpress and eBay."
