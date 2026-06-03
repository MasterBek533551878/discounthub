param(
  [string]$PublisherId = '2906853',
  [Parameter(Mandatory=$true)][string]$DatafeedApiKey,
  [string]$FeedListUrl = '',
  [int]$MaxFeeds = 20,
  [int]$MaxItemsPerFeed = 80,
  [int]$MinDiscountPercent = 10,
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

function Mask-Secret([string]$Value) {
  if ([string]::IsNullOrWhiteSpace($Value)) { return 'empty' }
  if ($Value.Length -le 8) { return 'configured' }
  return $Value.Substring(0, 4) + '...' + $Value.Substring($Value.Length - 4)
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

$lines = Set-EnvLine $lines 'AWIN_PUBLISHER_ID' $PublisherId
$lines = Set-EnvLine $lines 'AWIN_DATAFEED_API_KEY' $DatafeedApiKey
$lines = Set-EnvLine $lines 'AWIN_FEED_LIST_URL' $FeedListUrl
$lines = Set-EnvLine $lines 'AWIN_FEED_LIST_ENDPOINT_TEMPLATE' 'https://productdata.awin.com/datafeed/list/apikey/{api_key}'
$lines = Set-EnvLine $lines 'AWIN_FEED_MAX_FEEDS' ([string]$MaxFeeds)
$lines = Set-EnvLine $lines 'AWIN_FEED_MAX_ITEMS_PER_FEED' ([string]$MaxItemsPerFeed)
$lines = Set-EnvLine $lines 'AWIN_FEED_MIN_DISCOUNT_PERCENT' ([string]$MinDiscountPercent)

$fullEnvPath = [System.IO.Path]::GetFullPath($EnvPath)
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllLines($fullEnvPath, $lines, $utf8NoBom)

Write-Host 'Awin credentials saved to:' -ForegroundColor Green
Write-Host "  $EnvPath"
Write-Host ''
Write-Host 'Saved fields:'
Write-Host "  AWIN_PUBLISHER_ID: $PublisherId"
Write-Host "  AWIN_DATAFEED_API_KEY: $(Mask-Secret $DatafeedApiKey)"
Write-Host "  AWIN_FEED_LIST_URL: $(if ($FeedListUrl) { 'configured' } else { 'empty; backend will build URL from key' })"
Write-Host "  AWIN_FEED_MAX_FEEDS: $MaxFeeds"
Write-Host "  AWIN_FEED_MAX_ITEMS_PER_FEED: $MaxItemsPerFeed"
Write-Host "  AWIN_FEED_MIN_DISCOUNT_PERCENT: $MinDiscountPercent"
Write-Host ''
Write-Host 'Restart backend after changing .env.' -ForegroundColor Yellow
