param(
  [Parameter(Mandatory=$true)][string]$ClientId,
  [Parameter(Mandatory=$true)][string]$ClientSecret,
  [string]$CampaignId = '',
  [string]$ReferenceId = 'discounthub',
  [string]$MarketplaceId = 'EBAY_US',
  [string]$Scope = 'https://api.ebay.com/oauth/api_scope',
  [string]$OAuthUrl = 'https://api.ebay.com/identity/v1/oauth2/token',
  [string]$ApiBaseUrl = 'https://api.ebay.com',
  [string]$EnvPath = "$PSScriptRoot\..\.env"
)

$ErrorActionPreference = 'Stop'

function Set-EnvLine([string[]]$Lines, [string]$Name, [string]$Value) {
  $escapedName = [regex]::Escape($Name)
  $next = New-Object System.Collections.Generic.List[string]
  $found = $false

  foreach ($line in $Lines) {
    if ($line -match "^$escapedName=") {
      $next.Add("$Name=$Value")
      $found = $true
    } else {
      $next.Add($line)
    }
  }

  if (-not $found) {
    $next.Add("$Name=$Value")
  }

  return $next.ToArray()
}

$envDir = Split-Path $EnvPath -Parent
if (-not (Test-Path $envDir)) {
  New-Item -ItemType Directory -Path $envDir -Force | Out-Null
}

if (Test-Path $EnvPath) {
  $lines = @(Get-Content $EnvPath)
} else {
  $lines = @()
}

$lines = Set-EnvLine $lines 'EBAY_CLIENT_ID' $ClientId
$lines = Set-EnvLine $lines 'EBAY_CLIENT_SECRET' $ClientSecret
$lines = Set-EnvLine $lines 'EBAY_SCOPE' $Scope
$lines = Set-EnvLine $lines 'EBAY_OAUTH_URL' $OAuthUrl
$lines = Set-EnvLine $lines 'EBAY_API_BASE_URL' $ApiBaseUrl
$lines = Set-EnvLine $lines 'EBAY_DEFAULT_MARKETPLACE_ID' $MarketplaceId
$lines = Set-EnvLine $lines 'EBAY_CAMPAIGN_ID' $CampaignId
$lines = Set-EnvLine $lines 'EBAY_REFERENCE_ID' $ReferenceId

$fullEnvPath = [System.IO.Path]::GetFullPath($EnvPath)
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllLines($fullEnvPath, $lines, $utf8NoBom)

Write-Host 'eBay credentials saved to:' -ForegroundColor Green
Write-Host "  $EnvPath"
Write-Host ''
Write-Host 'Saved fields:'
Write-Host "  EBAY_CLIENT_ID: configured"
Write-Host "  EBAY_CLIENT_SECRET: configured"
Write-Host "  EBAY_DEFAULT_MARKETPLACE_ID: $MarketplaceId"
Write-Host "  EBAY_CAMPAIGN_ID: $(if ($CampaignId) { 'configured' } else { 'empty' })"
Write-Host "  EBAY_REFERENCE_ID: $ReferenceId"
Write-Host ''
Write-Host 'Restart backend after changing .env.' -ForegroundColor Yellow
