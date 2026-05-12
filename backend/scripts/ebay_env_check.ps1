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

$clientId = Get-EnvValue 'EBAY_CLIENT_ID'
$clientSecret = Get-EnvValue 'EBAY_CLIENT_SECRET'
$scope = Get-EnvValue 'EBAY_SCOPE'
$marketplace = Get-EnvValue 'EBAY_DEFAULT_MARKETPLACE_ID'

Write-Host 'DiscountHub eBay Browse API env check' -ForegroundColor Cyan
Write-Host "EBAY_CLIENT_ID configured:     $([bool]$clientId)"
Write-Host "EBAY_CLIENT_SECRET configured: $([bool]$clientSecret)"
Write-Host "EBAY_SCOPE:                    $scope"
Write-Host "EBAY_DEFAULT_MARKETPLACE_ID:   $marketplace"

if (-not $clientId -or -not $clientSecret) {
  Write-Host ''
  Write-Host 'Missing eBay credentials. The adapter is installed, but eBay providers must stay disabled until credentials are added.' -ForegroundColor Yellow
  Write-Host 'Create keys in eBay Developer Program, then add EBAY_CLIENT_ID and EBAY_CLIENT_SECRET to backend/.env.'
  exit 1
}

Write-Host 'eBay credentials are configured.' -ForegroundColor Green
