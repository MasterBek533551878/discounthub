param(
  [string]$DbPath = 'backend/data/discounthub.sqlite3',
  [string]$ReportPath = 'backend/data/stage69_ebay_link_report.csv',
  [int]$Limit = 0,
  [int]$TimeoutSeconds = 12,
  [double]$SleepSeconds = 0.15,
  [switch]$Delete
)

$ErrorActionPreference = 'Stop'

Write-Host '== DiscountHub Stage 69: eBay dead-link cleanup ==' -ForegroundColor Cyan
Write-Host "DB:      $DbPath"
Write-Host "Report:  $ReportPath"
Write-Host "Limit:   $Limit"
Write-Host "Mode:    $(@('dry-run','delete')[[bool]$Delete])"
Write-Host ''

if (-not (Test-Path $DbPath)) {
  throw "SQLite DB was not found: $DbPath"
}

$scriptPath = Join-Path $PSScriptRoot 'stage69_cleanup_ebay_dead_links.py'
if (-not (Test-Path $scriptPath)) {
  throw "Python helper was not found: $scriptPath"
}

$argsList = @(
  $scriptPath,
  '--db', $DbPath,
  '--report', $ReportPath,
  '--limit', $Limit,
  '--timeout', $TimeoutSeconds,
  '--sleep', $SleepSeconds
)

if ($Delete) {
  $argsList += '--delete'
}

python @argsList

Write-Host ''
Write-Host 'Stage 69 completed.' -ForegroundColor Green
