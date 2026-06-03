param(
  [string]$ApiBaseUrl = "http://127.0.0.1:8000",
  [string]$AdminToken = "",
  [string]$EnvPath = "backend/.env",
  [string]$ProviderId = "awin_feed_list",
  [int]$MaxFeeds = 20,
  [int]$MaxItemsPerFeed = 80,
  [int]$MinDiscountPercent = 10,
  [int]$TimeoutSeconds = 60,
  [bool]$SyncAfterRegister = $true
)

$ErrorActionPreference = "Stop"

function Read-EnvValue {
  param([string]$Name, [string]$Path = "backend/.env")

  $fromProcess = [Environment]::GetEnvironmentVariable($Name)
  if (![string]::IsNullOrWhiteSpace($fromProcess)) { return $fromProcess }

  if (!(Test-Path $Path)) { return "" }
  $line = Get-Content -Path $Path -Encoding UTF8 | Where-Object { $_ -match "^$([regex]::Escape($Name))=" } | Select-Object -First 1
  if (!$line) { return "" }
  $value = [string]($line -replace "^$([regex]::Escape($Name))=", "")
  $value = $value.Trim()
  if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
    $value = $value.Substring(1, $value.Length - 2)
  }
  return $value
}

function Mask-Configured {
  param([string]$Value)
  if ([string]::IsNullOrWhiteSpace($Value)) { return "missing" }
  return "configured"
}

if ([string]::IsNullOrWhiteSpace($AdminToken)) {
  $AdminToken = Read-EnvValue -Name "ADMIN_API_TOKEN" -Path $EnvPath
}
if ([string]::IsNullOrWhiteSpace($AdminToken)) {
  $AdminToken = "dev-local-admin-token"
}

$publisherId = Read-EnvValue -Name "AWIN_PUBLISHER_ID" -Path $EnvPath
$datafeedKey = Read-EnvValue -Name "AWIN_DATAFEED_API_KEY" -Path $EnvPath
$feedListUrl = Read-EnvValue -Name "AWIN_FEED_LIST_URL" -Path $EnvPath

Write-Host "== DiscountHub Stage 58: enable Awin + refresh live filters =="
Write-Host "API: $ApiBaseUrl"
Write-Host "Env: $EnvPath"
Write-Host "AWIN_PUBLISHER_ID: $(Mask-Configured $publisherId)"
Write-Host "AWIN_DATAFEED_API_KEY: $(Mask-Configured $datafeedKey)"
Write-Host "AWIN_FEED_LIST_URL: $(Mask-Configured $feedListUrl)"
Write-Host ""

if ([string]::IsNullOrWhiteSpace($datafeedKey) -and [string]::IsNullOrWhiteSpace($feedListUrl)) {
  throw "Awin is not configured. Fill AWIN_DATAFEED_API_KEY or AWIN_FEED_LIST_URL in $EnvPath first."
}

$health = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/health" -TimeoutSec 10
Write-Host "Backend health: $($health.status) ($($health.service))"

$headers = @{ "X-Admin-Token" = $AdminToken }
$providerUrl = "awin://feed-list?max_feeds=$MaxFeeds&max_items_per_feed=$MaxItemsPerFeed&min_discount_percent=$MinDiscountPercent&joined_only=true"
$provider = [ordered]@{
  id = $ProviderId
  name = "Awin Product Feed List - joined advertisers"
  url = $providerUrl
  adapter = "awin_feed_list_api"
  enabled = $true
  replaceOnSync = $false
  monetizationMode = "affiliate"
}

Write-Host "Registering/enabling provider: $ProviderId"
$result = Invoke-RestMethod -Method Post -Uri "$ApiBaseUrl/admin/feed-providers" -Headers $headers -ContentType "application/json" -Body ($provider | ConvertTo-Json -Depth 8) -TimeoutSec 30
Write-Host "Provider enabled: $($result.enabled), adapter=$($result.adapter), monetization=$($result.monetizationMode)"

if ($SyncAfterRegister) {
  Write-Host "Syncing Awin feed list. This may take a little while..."
  try {
    $sync = Invoke-RestMethod -Method Post -Uri "$ApiBaseUrl/admin/feed-providers/$ProviderId/sync?timeout_seconds=$TimeoutSeconds" -Headers $headers -TimeoutSec ($TimeoutSeconds + 10)
    Write-Host "Sync status: $($sync.status); imported=$($sync.importedCount); total=$($sync.dealCount)"
  } catch {
    Write-Warning "Awin sync failed. The provider is still enabled, so it will retry on the scheduler. Error: $($_.Exception.Message)"
  }
}

Write-Host ""
Write-Host "Live filter facets after sync/register:"
$facets = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals/facets" -TimeoutSec 30
Write-Host "Total deals: $($facets.total)"
Write-Host "Marketplaces returned to app filter: $(@($facets.marketplaces).Count)"
@($facets.marketplaces) | Select-Object -First 30 id, count | Format-Table -AutoSize
Write-Host "Monetization modes:"
@($facets.monetizationModes) | Select-Object id, count | Format-Table -AutoSize
Write-Host ""
Write-Host "Done. After this, restart/reopen the Flutter app or pull-to-refresh; the marketplace filter will use these live facets."
