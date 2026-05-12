param(
  [string]$Query = 'wireless headphones',
  [string]$MarketplaceId = '',
  [int]$Limit = 5,
  [string]$Filter = '',
  [string]$Sort = '',
  [string]$EnvPath = "$PSScriptRoot\..\.env"
)

$ErrorActionPreference = 'Stop'

function Get-EnvValue([string]$Name, [string]$Default = '') {
  $value = [Environment]::GetEnvironmentVariable($Name)
  if ($value) { return $value }
  if (Test-Path $EnvPath) {
    $line = Get-Content $EnvPath | Where-Object { $_ -match "^$Name=" } | Select-Object -First 1
    if ($line) { return ($line -replace "^$Name=", '').Trim() }
  }
  return $Default
}

$clientId = Get-EnvValue 'EBAY_CLIENT_ID'
$clientSecret = Get-EnvValue 'EBAY_CLIENT_SECRET'
$scope = Get-EnvValue 'EBAY_SCOPE' 'https://api.ebay.com/oauth/api_scope'
$oauthUrl = Get-EnvValue 'EBAY_OAUTH_URL' 'https://api.ebay.com/identity/v1/oauth2/token'
$apiBaseUrl = Get-EnvValue 'EBAY_API_BASE_URL' 'https://api.ebay.com'
if (-not $MarketplaceId) { $MarketplaceId = Get-EnvValue 'EBAY_DEFAULT_MARKETPLACE_ID' 'EBAY_US' }
$campaignId = Get-EnvValue 'EBAY_CAMPAIGN_ID'
$referenceId = Get-EnvValue 'EBAY_REFERENCE_ID' 'discounthub'

if (-not $clientId -or -not $clientSecret) {
  throw 'EBAY_CLIENT_ID and EBAY_CLIENT_SECRET are required. Use ebay_write_env.ps1 first.'
}

Write-Host 'DiscountHub eBay Browse API smoke test' -ForegroundColor Cyan
Write-Host "Query:       $Query"
Write-Host "Marketplace: $MarketplaceId"
Write-Host "Limit:       $Limit"
if ($Filter) { Write-Host "Filter:      $Filter" }
if ($Sort) { Write-Host "Sort:        $Sort" }

$pair = "${clientId}:${clientSecret}"
$bytes = [System.Text.Encoding]::ASCII.GetBytes($pair)
$basic = [Convert]::ToBase64String($bytes)
$tokenBody = "grant_type=client_credentials&scope=$([System.Uri]::EscapeDataString($scope))"
$tokenResponse = Invoke-RestMethod -Uri $oauthUrl -Method Post -Headers @{
  Authorization = "Basic $basic"
  'Content-Type' = 'application/x-www-form-urlencoded'
  Accept = 'application/json'
} -Body $tokenBody -TimeoutSec 30

$token = [string]$tokenResponse.access_token
if (-not $token) { throw 'OAuth token response did not include access_token.' }

$params = @{
  q = $Query
  limit = $Limit
  fieldgroups = 'EXTENDED'
}
if ($Filter) { $params.filter = $Filter }
if ($Sort) { $params.sort = $Sort }
$queryString = ($params.GetEnumerator() | ForEach-Object {
  "$([System.Uri]::EscapeDataString($_.Key))=$([System.Uri]::EscapeDataString([string]$_.Value))"
}) -join '&'

$url = "$($apiBaseUrl.TrimEnd('/'))/buy/browse/v1/item_summary/search?$queryString"
$headers = @{
  Authorization = "Bearer $token"
  Accept = 'application/json'
  'X-EBAY-C-MARKETPLACE-ID' = $MarketplaceId
}

$endUserCtx = @()
if ($campaignId) { $endUserCtx += "affiliateCampaignId=$campaignId" }
if ($referenceId) { $endUserCtx += "affiliateReferenceId=$referenceId" }
if ($endUserCtx.Count -gt 0) {
  $headers['X-EBAY-C-ENDUSERCTX'] = ($endUserCtx -join ',')
}

try {
  $response = Invoke-RestMethod -Uri $url -Method Get -Headers $headers -TimeoutSec 30
} catch {
  Write-Host 'FAILED' -ForegroundColor Red
  Write-Host $_.Exception.Message
  if ($_.Exception.Response) {
    try {
      $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
      $bodyText = $reader.ReadToEnd()
      Write-Host $bodyText
    } catch {}
  }
  exit 1
}

$items = @($response.itemSummaries)
Write-Host "OK: received $($items.Count) item summaries." -ForegroundColor Green
Write-Host ''
$items | Select-Object -First $Limit | ForEach-Object {
  $price = ''
  if ($_.price) { $price = "$($_.price.value) $($_.price.currency)" }
  $affiliate = [bool]$_.itemAffiliateWebUrl
  [pscustomobject]@{
    Title = $_.title
    Price = $price
    ItemId = $_.itemId
    AffiliateUrl = $affiliate
  }
} | Format-Table -AutoSize

if (-not $campaignId) {
  Write-Host ''
  Write-Host 'Note: EBAY_CAMPAIGN_ID is empty, so itemAffiliateWebUrl may not be returned.' -ForegroundColor Yellow
}
