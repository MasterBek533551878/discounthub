param(
  [string]$ApiBaseUrl = "http://127.0.0.1:8000",
  [string]$AdminToken = "",
  [string]$EnvPath = "backend/.env",
  [string]$ProviderId = "awin_feed_list",
  [int]$MaxFeeds = 10,
  [int]$MaxItemsPerFeed = 80,
  [int]$MinDiscountPercent = 0,
  [bool]$JoinedOnly = $true,
  [int]$TimeoutSeconds = 180,
  [switch]$NoSync
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

function Get-ErrorBody {
  param($ErrorRecord)
  try {
    $response = $ErrorRecord.Exception.Response
    if ($null -eq $response) { return "" }
    $stream = $response.GetResponseStream()
    if ($null -eq $stream) { return "" }
    $reader = New-Object System.IO.StreamReader($stream)
    return $reader.ReadToEnd()
  } catch {
    return ""
  }
}

function Invoke-ApiJson {
  param(
    [string]$Method,
    [string]$Uri,
    [hashtable]$Headers = @{},
    [object]$Body = $null,
    [int]$TimeoutSec = 30
  )

  try {
    if ($null -eq $Body) {
      return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $Headers -TimeoutSec $TimeoutSec
    }
    return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $Headers -ContentType "application/json" -Body ($Body | ConvertTo-Json -Depth 12) -TimeoutSec $TimeoutSec
  } catch {
    Write-Host ""
    Write-Warning "Request failed: $Method $Uri"
    Write-Warning $_.Exception.Message
    $bodyText = Get-ErrorBody $_
    if (![string]::IsNullOrWhiteSpace($bodyText)) {
      Write-Host "Response body:" -ForegroundColor Yellow
      Write-Host $bodyText
    }
    throw
  }
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

Write-Host "== DiscountHub Stage 60: Awin diagnose + sync =="
Write-Host "API: $ApiBaseUrl"
Write-Host "Env: $EnvPath"
Write-Host "AWIN_PUBLISHER_ID: $(Mask-Configured $publisherId)"
Write-Host "AWIN_DATAFEED_API_KEY: $(Mask-Configured $datafeedKey)"
Write-Host "AWIN_FEED_LIST_URL: $(Mask-Configured $feedListUrl)"
Write-Host "JoinedOnly: $JoinedOnly"
Write-Host "MinDiscountPercent: $MinDiscountPercent"
Write-Host "MaxFeeds: $MaxFeeds"
Write-Host "MaxItemsPerFeed: $MaxItemsPerFeed"
Write-Host ""

if ([string]::IsNullOrWhiteSpace($datafeedKey) -and [string]::IsNullOrWhiteSpace($feedListUrl)) {
  throw "Awin is not configured. Fill AWIN_DATAFEED_API_KEY or AWIN_FEED_LIST_URL in $EnvPath first."
}

$health = Invoke-ApiJson -Method Get -Uri "$ApiBaseUrl/health" -TimeoutSec 10
Write-Host "Backend health: $($health.status) ($($health.service))"

$headers = @{ "X-Admin-Token" = $AdminToken }
$awinImportedNow = $false
$awinSyncSucceeded = $false
$joinedValue = if ($JoinedOnly) { "true" } else { "false" }
$providerUrl = "awin://feed-list?max_feeds=$MaxFeeds&max_items_per_feed=$MaxItemsPerFeed&min_discount_percent=$MinDiscountPercent&joined_only=$joinedValue"
$provider = [ordered]@{
  id = $ProviderId
  name = "Awin Product Feed List - joined advertisers"
  url = $providerUrl
  adapter = "awin_feed_list_api"
  enabled = $true
  replaceOnSync = $false
  monetizationMode = "affiliate"
}

Write-Host ""
Write-Host "[1/5] Upserting provider"
$result = Invoke-ApiJson -Method Post -Uri "$ApiBaseUrl/admin/feed-providers" -Headers $headers -Body $provider -TimeoutSec 30
Write-Host "Provider: enabled=$($result.enabled), adapter=$($result.adapter), monetization=$($result.monetizationMode)"
Write-Host "Provider URL: $($result.url)"

Write-Host ""
Write-Host "[2/5] Last Awin sync logs before sync"
try {
  $runsBefore = Invoke-ApiJson -Method Get -Uri "$ApiBaseUrl/admin/feed-providers/sync-runs?provider_id=$ProviderId&limit=5" -Headers $headers -TimeoutSec 30
  @($runsBefore.items) | Select-Object startedAt,status,importedCount,dealCount,message | Format-List
} catch {
  Write-Warning "Could not read previous sync logs. Continuing."
}

if (!$NoSync) {
  Write-Host ""
  Write-Host "[3/5] Syncing provider"
  try {
    $sync = Invoke-ApiJson -Method Post -Uri "$ApiBaseUrl/admin/feed-providers/$ProviderId/sync?timeout_seconds=$TimeoutSeconds" -Headers $headers -TimeoutSec ($TimeoutSeconds + 15)
    Write-Host "Sync status: $($sync.status); imported=$($sync.importedCount); total=$($sync.dealCount)"
    if ($sync.message) { Write-Host "Message: $($sync.message)" }
    $awinSyncSucceeded = ($sync.status -eq "success" -or $sync.status -eq "ok")
    $awinImportedNow = ([int]$sync.importedCount -gt 0)
  } catch {
    Write-Warning "Awin sync failed. The exact HTTP body above or latest sync logs below should show the reason."
  }
} else {
  Write-Host ""
  Write-Host "[3/5] Sync skipped because -NoSync was passed."
}

Write-Host ""
Write-Host "[4/5] Last Awin sync logs after sync"
try {
  $runsAfter = Invoke-ApiJson -Method Get -Uri "$ApiBaseUrl/admin/feed-providers/sync-runs?provider_id=$ProviderId&limit=10" -Headers $headers -TimeoutSec 30
  @($runsAfter.items) | Select-Object startedAt,status,importedCount,dealCount,message | Format-List
} catch {
  Write-Warning "Could not read sync logs."
}

Write-Host ""
Write-Host "[5/5] Live app facets"
$facets = Invoke-ApiJson -Method Get -Uri "$ApiBaseUrl/deals/facets" -TimeoutSec 30
$marketplaces = @($facets.marketplaces)
$nonEbay = @($marketplaces | Where-Object { $_.id -notlike "eBay*" })
$monetizationModes = @($facets.monetizationModes)
$affiliateMode = $monetizationModes | Where-Object { $_.id -eq "affiliate" } | Select-Object -First 1
$affiliateCount = if ($affiliateMode) { [int]$affiliateMode.count } else { 0 }
Write-Host "Total deals: $($facets.total)"
Write-Host "Marketplace filter items: $($marketplaces.Count)"
Write-Host "Non-eBay marketplace filter items: $($nonEbay.Count)"
Write-Host "Affiliate monetization deals: $affiliateCount"
Write-Host ""
Write-Host "Top marketplaces:"
$marketplaces | Select-Object -First 30 id,count | Format-Table -AutoSize
Write-Host "Monetization modes:"
$monetizationModes | Select-Object id,count | Format-Table -AutoSize

if ($awinImportedNow) {
  Write-Host "Awin sync imported products in this run." -ForegroundColor Green
} elseif ($affiliateCount -gt 0) {
  Write-Warning "There are affiliate deals in the database, but this Awin run imported 0 products. Check the latest sync diagnostics above."
} else {
  Write-Warning "Awin did NOT import products yet. Non-eBay direct marketplaces may already be visible, but they are not Awin affiliate imports. Check the latest sync diagnostics above."
}
