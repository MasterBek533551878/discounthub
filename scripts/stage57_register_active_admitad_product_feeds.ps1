param(
  [string]$EnvPath = "backend/.env",
  [string]$ApiBaseUrl = "http://127.0.0.1:8000",
  [string]$AdminToken = "",
  [string]$Scope = "advcampaigns advcampaigns_for_website websites",
  [int]$Limit = 100,
  [switch]$SyncAfterRegister,
  [int]$TimeoutSeconds = 60,
  [int]$MaxItemsPerFeed = 2000,
  [int]$MaxScanRows = 25000,
  [int]$MinDiscountPercent = 10,
  [string[]]$ExcludedProgramIds = @("6115"),
  [switch]$IncludeKnownBrokenAliExpressWW
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

function Add-DiscountHubFeedOptions {
  param(
    [Parameter(Mandatory=$true)][string]$Url,
    [int]$MaxItemsPerFeed = 2000,
    [int]$MaxScanRows = 25000,
    [int]$MinDiscountPercent = 10,
    [string]$PlatformName = ""
  )

  $separator = "#"
  if ($Url.Contains("#")) { $separator = "&" }
  $localOptions = "discounthub_max_items=$MaxItemsPerFeed&discounthub_max_scan_rows=$MaxScanRows&discounthub_min_discount_percent=$MinDiscountPercent"
  if (![string]::IsNullOrWhiteSpace($PlatformName)) {
    $encodedPlatformName = [uri]::EscapeDataString($PlatformName)
    $localOptions = "$localOptions&discounthub_platform_name=$encodedPlatformName"
  }
  return ("{0}{1}{2}" -f $Url, $separator, $localOptions)
}

function Get-AdmitadCsvFeedUrl {
  param($Program)

  if (![string]::IsNullOrWhiteSpace([string]$Program.products_csv_link)) {
    return [string]$Program.products_csv_link
  }

  $feeds = @($Program.feeds_info)
  foreach ($feed in $feeds) {
    if (![string]::IsNullOrWhiteSpace([string]$feed.csv_link)) {
      return [string]$feed.csv_link
    }
  }

  return ""
}

Write-Host "== DiscountHub Stage 57 register active Admitad product feeds =="
Write-Host "API: $ApiBaseUrl"
Write-Host "Env: $EnvPath"
Write-Host ""

$health = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/health"
Write-Host "Backend health: $($health.status) ($($health.service))"

if ([string]::IsNullOrWhiteSpace($AdminToken)) {
  $AdminToken = Get-AdminTokenFromEnv -EnvPath $EnvPath
}
if ([string]::IsNullOrWhiteSpace($AdminToken)) {
  $AdminToken = "dev-local-admin-token"
}

$settings = Get-AdmitadSettings -EnvPath $EnvPath
$token = Get-AdmitadAccessToken -Settings $settings -Scope $Scope
Write-Host "Admitad token: OK (not printed)"
Write-Host "Safe sync limits: maxItems=$MaxItemsPerFeed, maxScanRows=$MaxScanRows, minDiscount=$MinDiscountPercent%"
if ($ExcludedProgramIds.Count -gt 0 -and -not $IncludeKnownBrokenAliExpressWW) {
  Write-Host ("Excluded Admitad campaign IDs: {0}" -f ($ExcludedProgramIds -join ", "))
  Write-Host "Note: campaign 6115 (AliExpress WW) is excluded by default because real click tests opened the AliExpress homepage even when productUrl worked."
}

$active = Invoke-AdmitadGet -Settings $settings -AccessToken $token.access_token -PathAndQuery "/advcampaigns/website/$($settings.WebsiteId)/?limit=$Limit&connection_status=active&has_tool=products"
$activeItems = @(Get-AdmitadResultsArray $active)
Write-Host "Active product-feed programs returned: $($activeItems.Count)"

$headers = @{ "X-Admin-Token" = $AdminToken }
$registered = 0
$synced = 0
$skipped = @()
$failed = @()

foreach ($program in $activeItems) {
  $csvUrl = Get-AdmitadCsvFeedUrl -Program $program
  $programName = [string]$program.name
  $programId = [string]$program.id

  if ($ExcludedProgramIds -contains $programId -and -not $IncludeKnownBrokenAliExpressWW) {
    $skipped += "$programName ($programId) -> excluded by DiscountHub quarantine: deeplinks open marketplace homepage instead of product pages"
    continue
  }

  if ([string]::IsNullOrWhiteSpace($csvUrl)) {
    $skipped += "$programName ($programId) -> no CSV product feed URL in API response"
    continue
  }

  $slug = Get-SafeSlug -Value $programName
  $providerId = "admitad_$programId`_$slug`_v1"
  if ($providerId.Length -gt 80) {
    $providerId = $providerId.Substring(0, 80).Trim("_")
  }

  $safeCsvUrl = Add-DiscountHubFeedOptions -Url $csvUrl -MaxItemsPerFeed $MaxItemsPerFeed -MaxScanRows $MaxScanRows -MinDiscountPercent $MinDiscountPercent -PlatformName $programName

  $provider = [ordered]@{
    id = $providerId
    name = "Admitad - $programName"
    url = $safeCsvUrl
    adapter = "admitad_products"
    enabled = $true
    replaceOnSync = $false
    monetizationMode = "affiliate"
  }

  try {
    $body = $provider | ConvertTo-Json -Depth 8
    $result = Invoke-RestMethod -Method Post -Uri "$ApiBaseUrl/admin/feed-providers" -Headers $headers -ContentType "application/json" -Body $body
    $registered += 1
    Write-Host ("Registered: {0} [{1}]" -f $result.id, $result.name)

    if ($SyncAfterRegister) {
      $sync = Invoke-RestMethod -Method Post -Uri "$ApiBaseUrl/admin/feed-providers/$($result.id)/sync?timeout_seconds=$TimeoutSeconds" -Headers $headers
      $synced += 1
      Write-Host ("  Synced: {0}; imported={1}; total={2}" -f $sync.status, $sync.importedCount, $sync.dealCount)
    }
  } catch {
    $detail = Get-HttpErrorDetail $_
    $failed += "$programName ($programId) -> $detail"
    Write-Warning "Failed: $programName ($programId) -> $detail"
  }
}

Write-Host ""
Write-Host "Registered: $registered"
if ($SyncAfterRegister) { Write-Host "Synced: $synced" }
Write-Host "Skipped: $($skipped.Count)"
if ($skipped.Count -gt 0) {
  $skipped | Select-Object -First 20 | ForEach-Object { Write-Warning $_ }
}
if ($failed.Count -gt 0) {
  Write-Warning "Failures:"
  $failed | ForEach-Object { Write-Warning $_ }
}

if ($registered -eq 0) {
  Write-Warning "No Admitad product feed providers were registered. Most likely all joined programs are still under moderation or product feeds are not available yet."
}

Write-Host "Stage 57 Admitad product-feed registration completed."
