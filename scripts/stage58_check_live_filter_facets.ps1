param(
  [string]$ApiBaseUrl = "http://127.0.0.1:8000",
  [string]$AdminToken = "",
  [string]$EnvPath = "backend/.env"
)

$ErrorActionPreference = "Stop"

function Read-EnvValue {
  param([string]$Name, [string]$Path = "backend/.env")
  $fromProcess = [Environment]::GetEnvironmentVariable($Name)
  if (![string]::IsNullOrWhiteSpace($fromProcess)) { return $fromProcess }
  if (!(Test-Path $Path)) { return "" }
  $line = Get-Content -Path $Path -Encoding UTF8 | Where-Object { $_ -match "^$([regex]::Escape($Name))=" } | Select-Object -First 1
  if (!$line) { return "" }
  return ([string]($line -replace "^$([regex]::Escape($Name))=", "")).Trim(' ', '"', "'")
}

if ([string]::IsNullOrWhiteSpace($AdminToken)) {
  $AdminToken = Read-EnvValue -Name "ADMIN_API_TOKEN" -Path $EnvPath
}
if ([string]::IsNullOrWhiteSpace($AdminToken)) {
  $AdminToken = "dev-local-admin-token"
}

Write-Host "== DiscountHub Stage 58: live app filter facets check =="
Write-Host "API: $ApiBaseUrl"
Write-Host ""

$health = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/health" -TimeoutSec 10
Write-Host "Backend health: $($health.status) ($($health.service))"

$facets = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals/facets" -TimeoutSec 30
$marketplaces = @($facets.marketplaces)
$nonEbay = @($marketplaces | Where-Object { ([string]$_.id) -notlike "eBay*" })

Write-Host "Total deals: $($facets.total)"
Write-Host "Marketplace filter items: $($marketplaces.Count)"
Write-Host "Non-eBay marketplace filter items: $($nonEbay.Count)"
Write-Host ""
Write-Host "Top marketplaces visible in Flutter filter:"
$marketplaces | Select-Object -First 40 id, count | Format-Table -AutoSize
Write-Host ""
Write-Host "Categories visible in Flutter filter:"
@($facets.categories) | Select-Object id, count | Format-Table -AutoSize
Write-Host ""
Write-Host "Monetization modes visible in Flutter filter:"
@($facets.monetizationModes) | Select-Object id, count | Format-Table -AutoSize

try {
  $headers = @{ "X-Admin-Token" = $AdminToken }
  $providers = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/admin/feed-providers" -Headers $headers -TimeoutSec 30
  Write-Host ""
  Write-Host "Awin/Admitad providers:"
  @($providers.items | Where-Object { $_.id -match "awin|admitad" -or $_.name -match "Awin|Admitad" }) |
    Select-Object id, name, adapter, enabled, lastStatus, lastImportedCount |
    Format-Table -AutoSize
} catch {
  Write-Warning "Could not read admin provider list. Facets check above is still valid for the mobile app. Error: $($_.Exception.Message)"
}

if ($nonEbay.Count -eq 0) {
  Write-Warning "The app filter is still eBay-only because backend has no imported non-eBay deals yet. Enable/sync Awin or Admitad providers, then run this check again."
} else {
  Write-Host "OK: non-eBay marketplaces are already visible to the app filter." -ForegroundColor Green
}
