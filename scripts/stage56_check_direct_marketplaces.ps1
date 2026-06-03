param(
  [string]$ApiBaseUrl = "http://127.0.0.1:8000",
  [string]$AdminToken = "dev-local-admin-token"
)

$ErrorActionPreference = "Stop"

Write-Host "== DiscountHub Stage 56 direct marketplace check =="
Write-Host "API: $ApiBaseUrl"
Write-Host ""

$headers = @{ "X-Admin-Token" = $AdminToken }

Write-Host "[1/4] Health"
$health = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/health"
$health | ConvertTo-Json -Depth 8
Write-Host ""

Write-Host "[2/4] Direct marketplace providers"
$providers = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/admin/feed-providers" -Headers $headers
$directProviders = @($providers.items | Where-Object { $_.id -like "mercadolibre_*_direct_v1" })
[pscustomobject]@{
  totalProviders = $providers.total
  stage56DirectProviders = $directProviders.Count
  lastStatuses = @($directProviders | Select-Object id, enabled, adapter, monetizationMode, lastStatus, lastImportedCount | Select-Object -First 8)
} | ConvertTo-Json -Depth 8
Write-Host ""

Write-Host "[3/4] Facets without currency restriction"
$facets = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals/facets"
[pscustomobject]@{
  total = $facets.total
  marketplaces = $facets.marketplaces.Count
  categories = $facets.categories.Count
  currencies = $facets.currencies
  monetizationModes = $facets.monetizationModes
  topMarketplaces = @($facets.marketplaces | Select-Object -First 12)
} | ConvertTo-Json -Depth 10
Write-Host ""

Write-Host "[4/4] Sample Mercado Libre deals"
try {
  $sample = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals?platform=Mercado%20Libre%20Mexico&page_size=5&sort=discount_desc"
  [pscustomobject]@{
    total = $sample.total
    returned = $sample.items.Count
    firstItem = if ($sample.items.Count -gt 0) { $sample.items[0] } else { $null }
  } | ConvertTo-Json -Depth 8
} catch {
  Write-Warning "Sample query failed. This is not fatal if providers imported zero Mexico rows. Error: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "Stage 56 check completed."
