param(
  [string]$ApiBaseUrl = "http://127.0.0.1:8000",
  [string]$EnvPath = "backend/.env",
  [string]$AdminToken = "",
  [string]$ProviderId = "admitad_6115_aliexpress_ww_v1",
  [int]$TimeoutSeconds = 300,
  [int]$MaxItemsPerFeed = 2000,
  [int]$MaxScanRows = 25000,
  [int]$MinDiscountPercent = 10,
  [switch]$ForceKnownBrokenAliExpressWW
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot/stage57_common_admitad.ps1"

function Get-AdminTokenFromEnv {
  param([string]$EnvPath = "backend/.env")
  try {
    $envValues = Read-DiscountHubEnvFile -Path $EnvPath
    return [string]$envValues["ADMIN_API_TOKEN"]
  } catch {
    return ""
  }
}

if ([string]::IsNullOrWhiteSpace($AdminToken)) {
  $AdminToken = Get-AdminTokenFromEnv -EnvPath $EnvPath
}
if ([string]::IsNullOrWhiteSpace($AdminToken)) {
  $AdminToken = "dev-local-admin-token"
}
$headers = @{ "X-Admin-Token" = $AdminToken }

if (-not $ForceKnownBrokenAliExpressWW) {
  throw "Admitad AliExpress WW (campaign 6115) is quarantined: direct productUrl opens the product, but Admitad affiliate/deeplink URLs open the AliExpress homepage. Use -ForceKnownBrokenAliExpressWW only for diagnostics, not for production sync."
}

Write-Host "== DiscountHub Stage 64: Admitad AliExpress sync check =="
Write-Host "API: $ApiBaseUrl"
Write-Host "Provider: $ProviderId"
Write-Host "Safe limits: maxItems=$MaxItemsPerFeed, maxScanRows=$MaxScanRows, minDiscount=$MinDiscountPercent%, timeout=$TimeoutSeconds sec"
Write-Host ""

$health = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/health" -TimeoutSec 15
Write-Host "Backend health: $($health.status) ($($health.service))"

Write-Host ""
Write-Host "[1/5] Re-registering active Admitad feeds with safe limits"
& "$PSScriptRoot/stage57_register_active_admitad_product_feeds.ps1" `
  -EnvPath $EnvPath `
  -ApiBaseUrl $ApiBaseUrl `
  -AdminToken $AdminToken `
  -MaxItemsPerFeed $MaxItemsPerFeed `
  -MaxScanRows $MaxScanRows `
  -MinDiscountPercent $MinDiscountPercent `
  -IncludeKnownBrokenAliExpressWW

Write-Host ""
Write-Host "[2/5] Provider after registration"
try {
  $provider = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/admin/feed-providers/$ProviderId" -Headers $headers -TimeoutSec 30
  $provider | Select-Object id, name, adapter, enabled, monetizationMode, lastStatus, lastImportedCount | Format-List
} catch {
  $detail = Get-HttpErrorDetail $_
  throw "Could not read provider ${ProviderId}: $detail"
}

Write-Host ""
Write-Host "[3/5] Syncing Admitad provider"
try {
  $sync = Invoke-RestMethod -Method Post -Uri "$ApiBaseUrl/admin/feed-providers/$ProviderId/sync?timeout_seconds=$TimeoutSeconds" -Headers $headers -TimeoutSec ($TimeoutSeconds + 30)
  $sync | ConvertTo-Json -Depth 8
} catch {
  $detail = Get-HttpErrorDetail $_
  Write-Warning "Admitad sync failed: $detail"
}

Write-Host ""
Write-Host "[4/5] Last Admitad sync runs"
try {
  $runs = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/admin/feed-providers/sync-runs?provider_id=$ProviderId&limit=5" -Headers $headers -TimeoutSec 30
  @($runs.items) | Select-Object providerId, status, importedCount, dealCount, message, startedAt | Format-List
} catch {
  Write-Warning "Could not read Admitad sync logs: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "[5/5] Live facets after Admitad sync"
$facets = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals/facets" -TimeoutSec 60
Write-Host "Total deals: $($facets.total)"
Write-Host "Top marketplaces:"
@($facets.marketplaces) | Select-Object -First 30 id, count | Format-Table -AutoSize
Write-Host ""
Write-Host "Monetization modes:"
@($facets.monetizationModes) | Select-Object id, count | Format-Table -AutoSize

Write-Host ""
Write-Host "Quick Admitad marketplace sample:"
try {
  $sample = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals?platform=AliExpress%20WW&page_size=5&sort=newest" -TimeoutSec 30
  Write-Host ("AliExpress WW platform sample: total={0}; returned={1}" -f $sample.total, @($sample.items).Count)
  @($sample.items) | Select-Object -First 5 title, platform, currentPrice, oldPrice, discountPercent | Format-Table -AutoSize
} catch {
  Write-Warning "Could not read AliExpress WW sample: $($_.Exception.Message)"
}

Write-Host "Stage 64 Admitad check completed."
