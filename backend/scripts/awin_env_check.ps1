param(
  [string]$EnvPath = "$PSScriptRoot\..\.env"
)

$ErrorActionPreference = 'Stop'

function Get-EnvValue([string]$Name) {
  $value = [Environment]::GetEnvironmentVariable($Name)
  if ($value) { return $value }
  if (Test-Path $EnvPath) {
    $line = Get-Content $EnvPath | Where-Object { $_ -match "^$Name=" } | Select-Object -First 1
    if ($line) { return ($line -replace "^$Name=", '').Trim() }
  }
  return ''
}

function Mask-Secret([string]$Value) {
  if ([string]::IsNullOrWhiteSpace($Value)) { return 'empty' }
  if ($Value.Length -le 8) { return 'configured' }
  return $Value.Substring(0, 4) + '...' + $Value.Substring($Value.Length - 4)
}

$publisherId = Get-EnvValue 'AWIN_PUBLISHER_ID'
$datafeedApiKey = Get-EnvValue 'AWIN_DATAFEED_API_KEY'
$feedListUrl = Get-EnvValue 'AWIN_FEED_LIST_URL'
$maxFeeds = Get-EnvValue 'AWIN_FEED_MAX_FEEDS'
$maxItems = Get-EnvValue 'AWIN_FEED_MAX_ITEMS_PER_FEED'
$minDiscount = Get-EnvValue 'AWIN_FEED_MIN_DISCOUNT_PERCENT'

Write-Host 'DiscountHub Awin env check' -ForegroundColor Cyan
Write-Host "AWIN_PUBLISHER_ID:             $publisherId"
Write-Host "AWIN_DATAFEED_API_KEY:         $(Mask-Secret $datafeedApiKey)"
Write-Host "AWIN_FEED_LIST_URL configured: $([bool]$feedListUrl)"
Write-Host "AWIN_FEED_MAX_FEEDS:           $maxFeeds"
Write-Host "AWIN_FEED_MAX_ITEMS_PER_FEED:  $maxItems"
Write-Host "AWIN_FEED_MIN_DISCOUNT_PERCENT:$minDiscount"

if (-not $publisherId -or -not $datafeedApiKey) {
  Write-Host ''
  Write-Host 'Missing Awin values. Run scripts/awin_write_env.ps1 first.' -ForegroundColor Yellow
  exit 1
}

Write-Host 'Awin credentials are configured.' -ForegroundColor Green
