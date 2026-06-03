param(
  [string]$ApiBaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

Write-Host "== DiscountHub Stage 54b Flutter pagination check =="
Write-Host "API: $ApiBaseUrl"

Write-Host "`n[1/4] Backend health"
$health = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/health"
$health | ConvertTo-Json -Depth 6

Write-Host "`n[2/4] Facets endpoint"
$facets = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals/facets?currency=USD"
[PSCustomObject]@{
  total = $facets.total
  marketplaces = $facets.marketplaces.Count
  categories = $facets.categories.Count
  monetizationModes = $facets.monetizationModes.Count
} | ConvertTo-Json -Depth 6

Write-Host "`n[3/4] Paged deals endpoint"
$page1 = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals?sort=discount_desc&page=1&page_size=80&currency=USD"
$page2 = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals?sort=discount_desc&page=2&page_size=80&currency=USD"
[PSCustomObject]@{
  total = $page1.total
  page1Returned = $page1.items.Count
  page2Returned = $page2.items.Count
  page1FirstId = if ($page1.items.Count -gt 0) { $page1.items[0].id } else { $null }
  page2FirstId = if ($page2.items.Count -gt 0) { $page2.items[0].id } else { $null }
} | ConvertTo-Json -Depth 6

if ($page1.items.Count -eq 0) {
  throw "Page 1 returned no deals."
}

Write-Host "`n[4/4] Flutter analyze"
flutter analyze

Write-Host "`nStage 54b check completed."
