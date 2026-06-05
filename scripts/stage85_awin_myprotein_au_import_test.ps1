param(
  [string]$ApiBaseUrl = "http://127.0.0.1:8000",
  [string]$AdminToken = "",
  [string]$EnvPath = "backend/.env",
  [string]$ProviderId = "awin_myprotein_au_v1",
  [int]$MaxFeeds = 5,
  [int]$MaxItemsPerFeed = 500,
  [int]$MinDiscountPercent = 10,
  [int]$TimeoutSeconds = 120,
  [switch]$OpenBrowserTests
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

function Get-JsonProperty {
  param([object]$Object, [string]$Name)
  if ($null -eq $Object) { return $null }
  $prop = $Object.PSObject.Properties[$Name]
  if ($prop) { return $prop.Value }
  return $null
}

if ([string]::IsNullOrWhiteSpace($AdminToken)) {
  $AdminToken = Read-EnvValue -Name "ADMIN_API_TOKEN" -Path $EnvPath
}
if ([string]::IsNullOrWhiteSpace($AdminToken)) {
  $AdminToken = "dev-local-admin-token"
}

Write-Host "== DiscountHub Stage 85: Awin Myprotein AU local import test =="
Write-Host "API: $ApiBaseUrl"
Write-Host "Env: $EnvPath"
Write-Host "Provider: $ProviderId"
Write-Host "Advertiser: Myprotein AU / id=19155"
Write-Host "Limits: maxFeeds=$MaxFeeds, maxItemsPerFeed=$MaxItemsPerFeed, minDiscount=$MinDiscountPercent%, timeout=$TimeoutSeconds sec"
Write-Host ""

Write-Host "[1/5] Python compile check"
$pythonCandidates = @("backend\.venv\Scripts\python.exe", "py")
$python = $null
foreach ($candidate in $pythonCandidates) {
  if ($candidate -eq "py") {
    try {
      & py -3 --version *> $null
      if ($LASTEXITCODE -eq 0) { $python = "py"; break }
    } catch {}
  } elseif (Test-Path $candidate) {
    $python = $candidate
    break
  }
}
if (-not $python) { throw "Python was not found. Restore backend/.venv or install Python." }
if ($python -eq "py") {
  & py -3 -m py_compile backend/app/services/awin_feed_list_service.py
} else {
  & $python -m py_compile backend/app/services/awin_feed_list_service.py
}
if ($LASTEXITCODE -ne 0) { throw "Python compile failed" }

Write-Host ""
Write-Host "[2/5] Backend health"
$health = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/health" -TimeoutSec 10
Write-Host "Backend health: $($health.status) ($($health.service))"

$headers = @{ "X-Admin-Token" = $AdminToken }
$providerUrl = "awin://feed-list?advertiser_id=19155&advertiser_name=Myprotein%20AU&max_feeds=$MaxFeeds&max_items_per_feed=$MaxItemsPerFeed&min_discount_percent=$MinDiscountPercent&joined_only=true"
$provider = [ordered]@{
  id = $ProviderId
  name = "Awin - Myprotein AU"
  url = $providerUrl
  adapter = "awin_feed_list_api"
  enabled = $true
  replaceOnSync = $false
  monetizationMode = "affiliate"
}

Write-Host ""
Write-Host "[3/5] Register provider"
$result = Invoke-RestMethod -Method Post -Uri "$ApiBaseUrl/admin/feed-providers" -Headers $headers -ContentType "application/json" -Body ($provider | ConvertTo-Json -Depth 8) -TimeoutSec 30
Write-Host "Provider registered: enabled=$($result.enabled), adapter=$($result.adapter), monetization=$($result.monetizationMode)"
Write-Host "Provider URL: $($result.url)"

Write-Host ""
Write-Host "[4/5] Sync provider"
$sync = Invoke-RestMethod -Method Post -Uri "$ApiBaseUrl/admin/feed-providers/$ProviderId/sync?timeout_seconds=$TimeoutSeconds" -Headers $headers -TimeoutSec ($TimeoutSeconds + 30)
$sync | ConvertTo-Json -Depth 8
if ($sync.status -ne "ok") { throw "Sync did not return ok" }
if ([int]$sync.importedCount -le 0) { throw "Sync imported 0 deals" }

Write-Host ""
Write-Host "[5/5] Sample imported deals + click tests"
$platform = [Uri]::EscapeDataString("Myprotein AU")
$page = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals?platform=$platform&monetization_mode=affiliate&page_size=8&sort=newest" -TimeoutSec 30
Write-Host "Public API total for Myprotein AU affiliate: $($page.total)"
if ([int]$page.total -le 0) { throw "No Myprotein AU deals returned from public API" }

$items = @($page.items)
$idx = 0
foreach ($item in $items | Select-Object -First 8) {
  $idx++
  $id = Get-JsonProperty $item "id"
  $title = Get-JsonProperty $item "title"
  $discount = Get-JsonProperty $item "discountPercent"
  $old = Get-JsonProperty $item "oldPrice"
  $current = Get-JsonProperty $item "currentPrice"
  $currency = Get-JsonProperty $item "currency"
  $image = Get-JsonProperty $item "imageUrl"
  $productUrl = Get-JsonProperty $item "productUrl"
  $affiliateUrl = Get-JsonProperty $item "affiliateUrl"
  Write-Host "------------------------------------------------------------------------------------------------"
  Write-Host "[$idx] $id | discount=$discount% | $currency $old -> $current"
  Write-Host "title: $($title.Substring(0, [Math]::Min(120, $title.Length)))"
  Write-Host "image ok: $(-not [string]::IsNullOrWhiteSpace($image))"
  Write-Host "productUrl: $productUrl"
  Write-Host "affiliateUrl: $affiliateUrl"
  Write-Host "PowerShell browser test:"
  Write-Host "Start-Process `"$ApiBaseUrl/deals/$id/click`""
}

if ($OpenBrowserTests) {
  foreach ($item in $items | Select-Object -First 3) {
    $id = Get-JsonProperty $item "id"
    Start-Process "$ApiBaseUrl/deals/$id/click"
  }
}

Write-Host ""
Write-Host "Stage 85 Myprotein AU local import test completed. Manually open 2-3 /click links and confirm they land on product pages."
