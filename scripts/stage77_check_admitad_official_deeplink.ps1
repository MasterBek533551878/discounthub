param(
  [string]$EnvPath = "backend/.env",
  [string]$ApiBaseUrl = "https://api.discounthub.uz",
  [string]$DealId = "",
  [string]$Scope = "advcampaigns advcampaigns_for_website websites deeplink_generator",
  [switch]$OpenInBrowser
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot/stage57_common_admitad.ps1"

function Get-HeaderLocation {
  param([string]$Url)
  try {
    $response = Invoke-WebRequest -Uri $Url -MaximumRedirection 0 -ErrorAction SilentlyContinue
    return [string]$response.Headers.Location
  } catch {
    if ($_.Exception.Response -and $_.Exception.Response.Headers.Location) {
      return [string]$_.Exception.Response.Headers.Location
    }
    throw
  }
}

function Get-DeepLinkUrlsFromObject {
  param($Value)
  $urls = New-Object System.Collections.Generic.List[string]

  function Walk($Node) {
    if ($null -eq $Node) { return }
    if ($Node -is [string]) {
      if ($Node -match '^https?://' -and ($Node -match 'ad\.admitad\.com|rzekl\.com|rztekl\.com')) {
        [void]$urls.Add($Node)
      }
      return
    }
    if ($Node -is [System.Collections.IEnumerable] -and -not ($Node -is [string])) {
      foreach ($item in $Node) { Walk $item }
      return
    }
    $props = $Node.PSObject.Properties
    if ($props) {
      foreach ($prop in $props) { Walk $prop.Value }
    }
  }

  Walk $Value
  return @($urls | Select-Object -Unique)
}

function Get-CampaignIdFromProviderId {
  param([string]$ProviderId)
  if ($ProviderId -match '^admitad_(\d+)(?:_|$)') { return $Matches[1] }
  return ""
}

Write-Host "== DiscountHub Stage 77: Admitad official deeplink diagnosis =="
Write-Host "API: $ApiBaseUrl"
Write-Host "Env: $EnvPath"
Write-Host ""

$health = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/health"
Write-Host "Backend health: $($health.status) ($($health.environment))"

if ([string]::IsNullOrWhiteSpace($DealId)) {
  $sample = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals?platform=AliExpress&monetization_mode=affiliate&page_size=100&sort=newest"
  $deal = @($sample.items | Where-Object { $_.providerId -like 'admitad_*' } | Select-Object -First 1)[0]
  if ($null -eq $deal) {
    throw "No Admitad deal found in the first 100 AliExpress affiliate deals."
  }
} else {
  $deal = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals/$DealId"
}

Write-Host "Deal:"
$deal | Select-Object id,title,platform,providerId,productUrl,affiliateUrl | Format-List

$campaignId = Get-CampaignIdFromProviderId -ProviderId ([string]$deal.providerId)
if ([string]::IsNullOrWhiteSpace($campaignId)) {
  throw "Could not extract Admitad campaign id from providerId=$($deal.providerId)"
}
Write-Host "Campaign ID: $campaignId"
Write-Host ""

Write-Host "[1/3] Backend /click Location"
$backendLocation = Get-HeaderLocation -Url "$ApiBaseUrl/deals/$($deal.id)/click"
Write-Host $backendLocation
Write-Host "Contains ulp: $($backendLocation -match 'ulp=')"
Write-Host ""

Write-Host "[2/3] Admitad official Deeplink Generator API"
$settings = Get-AdmitadSettings -EnvPath $EnvPath
$token = Get-AdmitadAccessToken -Settings $settings -Scope $Scope
$productUrl = [string]$deal.productUrl
$encodedProductUrl = [uri]::EscapeDataString($productUrl)
$path = "/deeplink/$($settings.WebsiteId)/advcampaign/$campaignId/?ulp=$encodedProductUrl"
$official = Invoke-AdmitadGet -Settings $settings -AccessToken $token.access_token -PathAndQuery $path
$official | ConvertTo-Json -Depth 12
$officialUrls = @(Get-DeepLinkUrlsFromObject $official)
Write-Host ""
Write-Host "Official generated URL(s):"
if ($officialUrls.Count -eq 0) {
  Write-Warning "No Admitad tracking URL found in official generator response."
} else {
  $officialUrls | ForEach-Object { Write-Host $_ }
}
Write-Host ""

Write-Host "[3/3] Direct product URL to test manually"
Write-Host $productUrl
Write-Host ""

if ($OpenInBrowser) {
  Start-Process $productUrl
  Start-Process "$ApiBaseUrl/deals/$($deal.id)/click"
  foreach ($url in $officialUrls | Select-Object -First 1) { Start-Process $url }
}

Write-Host "Stage 77 diagnosis completed."
