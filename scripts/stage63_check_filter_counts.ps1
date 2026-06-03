param(
  [string]$ApiBaseUrl = "http://127.0.0.1:8000",
  [int]$PageSize = 50
)

$ErrorActionPreference = "Stop"

function Get-ApiJson {
  param([string]$Url)
  return Invoke-RestMethod -Method Get -Uri $Url -TimeoutSec 30
}

function Encode-QueryValue {
  param([string]$Value)
  return [System.Uri]::EscapeDataString($Value)
}

Write-Host "== DiscountHub Stage 63: filter count consistency check =="
Write-Host "API: $ApiBaseUrl"
Write-Host ""

$health = Get-ApiJson "$ApiBaseUrl/health"
Write-Host "Backend health: $($health.status) ($($health.service))"

$facets = Get-ApiJson "$ApiBaseUrl/deals/facets"
$page = Get-ApiJson "$ApiBaseUrl/deals?page_size=$PageSize&sort=discount_desc"
$items = @($page.items)
$badPageRows = @($items | Where-Object { $_.discountPercent -le 0 -or $_.oldPrice -le $_.currentPrice })

Write-Host "Facets total      : $($facets.total)"
Write-Host "Page items        : $($items.Count)"
Write-Host "Page total        : $($page.total)"
Write-Host "Bad rows on page  : $($badPageRows.Count)"
Write-Host ""
Write-Host "Top marketplaces:"
@($facets.marketplaces) | Select-Object -First 20 id,count | Format-Table -AutoSize
Write-Host "Monetization modes:"
@($facets.monetizationModes) | Select-Object id,count | Format-Table -AutoSize

$failures = @()
foreach ($marketplace in @($facets.marketplaces | Select-Object -First 30)) {
  $encoded = Encode-QueryValue ([string]$marketplace.id)
  $filtered = Get-ApiJson "$ApiBaseUrl/deals?platform=$encoded&page_size=20&sort=discount_desc"
  $filteredItems = @($filtered.items)
  $bad = @($filteredItems | Where-Object { $_.discountPercent -le 0 -or $_.oldPrice -le $_.currentPrice })
  if ($bad.Count -gt 0) {
    $sample = $bad[0]
    $failures += [pscustomobject]@{
      platform = $marketplace.id
      facetCount = $marketplace.count
      pageTotal = $filtered.total
      badRows = $bad.Count
      sample = $sample.title
    }
  }
  if ($filtered.total -ne $marketplace.count) {
    $failures += [pscustomobject]@{
      platform = $marketplace.id
      facetCount = $marketplace.count
      pageTotal = $filtered.total
      badRows = 0
      sample = "facet count != page total"
    }
  }
}

Write-Host ""
Write-Host "Marketplace-specific failures: $($failures.Count)"
if ($failures.Count -gt 0) {
  $failures | Format-Table -AutoSize
  throw "Filter counts or marketplace-specific discount rows are still inconsistent."
}

if ($badPageRows.Count -gt 0) { throw "Public API still returned non-discount rows." }
Write-Host "OK: counts and filters are discount-only and consistent." -ForegroundColor Green
