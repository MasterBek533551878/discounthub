param(
  [string]$ApiBaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

Write-Host "== DiscountHub Stage 54 Flutter filters check =="
Write-Host "API: $ApiBaseUrl"
Write-Host ""

Write-Host "[1/4] Backend facets endpoint"
$facets = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals/facets?currency=USD"
$facetsSummary = [ordered]@{
  total = $facets.total
  marketplaces = @($facets.marketplaces).Count
  categories = @($facets.categories).Count
  monetizationModes = @($facets.monetizationModes).Count
  priceRange = $facets.priceRange
}
$facetsSummary | ConvertTo-Json -Depth 8
Write-Host ""

Write-Host "[2/4] Backend filtered page used by Flutter"
$deals = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals?platform=eBay%20US&min_discount=20&page_size=5&sort=discount_desc"
$dealsSummary = [ordered]@{
  total = $deals.total
  returned = @($deals.items).Count
  firstPlatform = if (@($deals.items).Count -gt 0) { $deals.items[0].platform } else { $null }
  firstDiscount = if (@($deals.items).Count -gt 0) { $deals.items[0].discountPercent } else { $null }
}
$dealsSummary | ConvertTo-Json -Depth 8
Write-Host ""

Write-Host "[3/4] Flutter analyze"
if (Get-Command flutter -ErrorAction SilentlyContinue) {
  flutter analyze
} else {
  Write-Warning "Flutter command not found in PATH. Skipping flutter analyze."
}
Write-Host ""

Write-Host "[4/4] Stage 54 check completed."
