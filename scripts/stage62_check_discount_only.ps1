param(
  [string]$ApiBaseUrl = "http://127.0.0.1:8000",
  [int]$PageSize = 50
)

$ErrorActionPreference = "Stop"

Write-Host "== DiscountHub Stage 62b: discount-only API and filters check =="
Write-Host "API: $ApiBaseUrl"
Write-Host ""

$health = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/health" -TimeoutSec 10
Write-Host "Backend health: $($health.status) ($($health.service))"

$facets = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals/facets" -TimeoutSec 30
$page = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals?page_size=$PageSize&sort=discount_desc" -TimeoutSec 30
$items = @($page.items)
$bad = @($items | Where-Object { $_.discountPercent -le 0 -or $_.oldPrice -le $_.currentPrice })

Write-Host "Facets total      : $($facets.total)"
Write-Host "Page items        : $($items.Count)"
Write-Host "Page total        : $($page.total)"
Write-Host "Page hasNextPage  : $($page.hasNextPage)"
Write-Host "Bad rows on page  : $($bad.Count)"
Write-Host ""
Write-Host "Top deals:"
$items | Select-Object -First 15 platform,title,discountPercent,currentPrice,oldPrice | Format-Table -AutoSize
Write-Host ""
Write-Host "Top marketplaces:"
@($facets.marketplaces) | Select-Object -First 20 id,count | Format-Table -AutoSize
Write-Host "Monetization modes:"
@($facets.monetizationModes) | Select-Object id,count | Format-Table -AutoSize

$platformFailures = @()
foreach ($marketplace in @($facets.marketplaces | Select-Object -First 25)) {
  $encoded = [System.Uri]::EscapeDataString([string]$marketplace.id)
  $platformPage = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals?platform=$encoded&page_size=20&sort=discount_desc" -TimeoutSec 30
  $platformItems = @($platformPage.items)
  $badPlatformItems = @($platformItems | Where-Object { $_.discountPercent -le 0 -or $_.oldPrice -le $_.currentPrice })
  if ($badPlatformItems.Count -gt 0) {
    $platformFailures += [pscustomobject]@{
      platform = $marketplace.id
      badRows = $badPlatformItems.Count
      sample = $badPlatformItems[0].title
    }
  }
}

Write-Host ""
Write-Host "Platform-specific 0% check failures: $($platformFailures.Count)"
if ($platformFailures.Count -gt 0) {
  $platformFailures | Format-Table -AutoSize
}

if ($facets.total -le 0) { throw "No discount deals are visible." }
if ($bad.Count -gt 0) { throw "API returned one or more 0% rows on the top page." }
if ($platformFailures.Count -gt 0) { throw "One or more marketplace filters still return non-discount rows." }
Write-Host "OK: API and marketplace filters return only real discounts." -ForegroundColor Green
