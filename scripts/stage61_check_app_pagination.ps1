param(
  [string]$ApiBaseUrl = "http://127.0.0.1:8000",
  [int]$PageSize = 36
)

$ErrorActionPreference = "Stop"

Write-Host "== DiscountHub Stage 61: app pagination/API count check =="
Write-Host "API: $ApiBaseUrl"
Write-Host "PageSize: $PageSize"
Write-Host ""

$health = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/health" -TimeoutSec 10
Write-Host "Backend health: $($health.status) ($($health.name))"

$facets = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals/facets" -TimeoutSec 20
$page1 = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals?page=1&page_size=$PageSize&sort=discount_desc" -TimeoutSec 20
$page2 = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals?page=2&page_size=$PageSize&sort=discount_desc" -TimeoutSec 20

Write-Host ""
Write-Host "Facets total      : $($facets.total)"
Write-Host "Page 1 items      : $($page1.items.Count)"
Write-Host "Page 1 total      : $($page1.total)"
Write-Host "Page 1 hasNextPage: $($page1.hasNextPage)"
Write-Host "Page 2 items      : $($page2.items.Count)"
Write-Host "Page 2 total      : $($page2.total)"
Write-Host "Page 2 hasNextPage: $($page2.hasNextPage)"

Write-Host ""
Write-Host "Top marketplaces from facets:"
$facets.marketplaces | Select-Object -First 12 id,count | Format-Table -AutoSize

Write-Host "Top monetization modes from facets:"
$facets.monetizationModes | Select-Object id,count | Format-Table -AutoSize

Write-Host "Platforms on page 1:"
$page1.items | Group-Object platform | Sort-Object Count -Descending | Select-Object Name,Count | Format-Table -AutoSize

if ($page1.total -le $page1.items.Count) {
  Write-Warning "API page total is not larger than one page. The Flutter list may think there are no more deals."
} else {
  Write-Host "OK: API reports full catalogue total, not only the first page."
}

if ($page1.hasNextPage -ne $true) {
  Write-Warning "API did not report hasNextPage=true for page 1."
} else {
  Write-Host "OK: API pagination is available."
}
