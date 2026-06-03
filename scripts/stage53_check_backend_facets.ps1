param(
  [string]$ApiBaseUrl = "http://127.0.0.1:8000",
  [string]$AdminToken = "dev-local-admin-token"
)

$ErrorActionPreference = "Stop"

function Show-Json($value) {
  $value | ConvertTo-Json -Depth 8
}

Write-Host "== DiscountHub Stage 53 backend facets check ==" -ForegroundColor Cyan
Write-Host "API: $ApiBaseUrl"

Write-Host "`n[1/5] Health"
$health = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/health"
Show-Json $health

Write-Host "`n[2/5] Facets"
$facets = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals/facets?currency=USD"
Show-Json ([ordered]@{
  total = $facets.total
  marketplaces = $facets.marketplaces.Count
  categories = $facets.categories.Count
  countries = $facets.shippingCountries.Count
  currencies = $facets.currencies.Count
  monetizationModes = $facets.monetizationModes
  priceRange = $facets.priceRange
  discountRange = $facets.discountRange
})

Write-Host "`n[3/5] Server-side filtered deals"
$filtered = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals?platform=eBay%20US&min_discount=20&page_size=5&sort=discount_desc"
Show-Json ([ordered]@{
  total = $filtered.total
  pageSize = $filtered.pageSize
  firstItem = if ($filtered.items.Count -gt 0) { $filtered.items[0] } else { $null }
})

Write-Host "`n[4/5] Monetization filter"
$direct = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals?monetization_mode=direct&page_size=3"
Show-Json ([ordered]@{
  total = $direct.total
  returned = $direct.items.Count
  firstMode = if ($direct.items.Count -gt 0) { $direct.items[0].monetizationMode } else { $null }
})

Write-Host "`n[5/5] Feed provider contract"
$providers = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/admin/feed-providers" -Headers @{ "X-Admin-Token" = $AdminToken }
Show-Json ([ordered]@{
  total = $providers.total
  firstProvider = if ($providers.items.Count -gt 0) { $providers.items[0] } else { $null }
})

Write-Host "`nStage 53 check completed." -ForegroundColor Green
