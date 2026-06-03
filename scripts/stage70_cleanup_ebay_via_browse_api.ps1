param(
  [string]$DbPath = 'backend/data/discounthub.sqlite3',
  [string]$EnvPath = 'backend/.env',
  [string]$ReportPath = 'backend/data/stage70_ebay_browse_api_report.csv',
  [int]$Limit = 0,
  [int]$TimeoutSeconds = 20,
  [double]$SleepSeconds = 0.08,
  [switch]$Delete,
  [switch]$UpdateLinks
)

$ErrorActionPreference = 'Stop'

Write-Host '== DiscountHub Stage 70: eBay cleanup via official Browse API ==' -ForegroundColor Cyan
Write-Host "DB:           $DbPath"
Write-Host "Env:          $EnvPath"
Write-Host "Report:       $ReportPath"
Write-Host "Limit:        $Limit"
Write-Host "Mode:         $(@('dry-run','delete')[[bool]$Delete])"
Write-Host "Update links: $([bool]$UpdateLinks)"
Write-Host ''

if (-not (Test-Path $DbPath)) {
  throw "SQLite DB was not found: $DbPath"
}
if (-not (Test-Path $EnvPath)) {
  throw "Backend .env file was not found: $EnvPath"
}

$scriptPath = Join-Path $PSScriptRoot 'stage70_cleanup_ebay_via_browse_api.py'
if (-not (Test-Path $scriptPath)) {
  throw "Python helper was not found: $scriptPath"
}

$argsList = @(
  $scriptPath,
  '--db', $DbPath,
  '--env', $EnvPath,
  '--report', $ReportPath,
  '--limit', $Limit,
  '--timeout', $TimeoutSeconds,
  '--sleep', $SleepSeconds
)

if ($Delete) { $argsList += '--delete' }
if ($UpdateLinks) { $argsList += '--update-links' }

python @argsList

Write-Host ''
Write-Host 'Stage 70 completed.' -ForegroundColor Green
