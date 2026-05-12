param(
  [string]$BaseUrl = 'http://127.0.0.1:8000',
  [string]$AdminToken = 'dev-local-admin-token',
  [string]$ConfigPath = "$PSScriptRoot\..\config\stage51_ebay_expansion_providers.json",
  [int]$TimeoutSeconds = 35,
  [int]$WaitSeconds = 20,
  [switch]$SkipMercadoLibreCleanup,
  [switch]$RegisterOnly
)

$ErrorActionPreference = 'Stop'

function Wait-BackendReady {
  param(
    [Parameter(Mandatory = $true)][string]$Url,
    [int]$Seconds = 20
  )

  $deadline = (Get-Date).AddSeconds($Seconds)
  do {
    try {
      Invoke-RestMethod -Uri "$Url/health" -Method Get -TimeoutSec 3 | Out-Null
      return
    } catch {
      Start-Sleep -Seconds 1
    }
  } while ((Get-Date) -lt $deadline)

  throw "Backend is not reachable at $Url. Start uvicorn in another PowerShell window first."
}

function Read-Stage51Providers {
  param(
    [Parameter(Mandatory = $true)][string]$Path
  )

  if (-not (Test-Path $Path)) {
    throw "Stage 51 provider config not found: $Path"
  }

  $json = Get-Content $Path -Raw -Encoding UTF8
  $parsed = $json | ConvertFrom-Json

  if ($null -eq $parsed) {
    return @()
  }

  # Windows PowerShell can sometimes keep a root JSON array as one object in a
  # pipeline expression. Force real item-by-item enumeration here.
  if ($parsed.PSObject.Properties.Name -contains 'providers') {
    return @(foreach ($item in $parsed.providers) { $item })
  }

  return @(foreach ($item in $parsed) { $item })
}

Wait-BackendReady -Url $BaseUrl -Seconds $WaitSeconds

$headers = @{ 'X-Admin-Token' = $AdminToken }

if (-not $SkipMercadoLibreCleanup.IsPresent) {
  Write-Host 'Checking for temporary Mercado Libre providers...' -ForegroundColor Cyan
  $current = Invoke-RestMethod -Uri "$BaseUrl/admin/feed-providers" -Method Get -Headers $headers -TimeoutSec 10
  $mlProviders = @($current.items | Where-Object { ([string]$_.id).StartsWith('mercadolibre_') })

  foreach ($provider in $mlProviders) {
    Write-Host "Removing temporary Mercado Libre provider: $($provider.id)" -ForegroundColor Yellow
    Invoke-RestMethod -Uri "$BaseUrl/admin/feed-providers/$($provider.id)" -Method Delete -Headers $headers -TimeoutSec 10 | Out-Null
  }

  if ($mlProviders.Count -eq 0) {
    Write-Host 'No temporary Mercado Libre providers found.' -ForegroundColor DarkGray
  }
}

$providers = Read-Stage51Providers -Path $ConfigPath
if ($providers.Count -eq 0) {
  Write-Host 'No Stage 51 eBay expansion providers found.' -ForegroundColor Yellow
  exit 0
}

Write-Host "Registering $($providers.Count) Stage 51 eBay expansion providers..." -ForegroundColor Cyan

$totalImported = 0
$successCount = 0
$failedCount = 0

foreach ($provider in $providers) {
  $providerId = [string]$provider.id
  if ([string]::IsNullOrWhiteSpace($providerId)) {
    Write-Host 'Skipping provider without id.' -ForegroundColor Yellow
    continue
  }

  try {
    Write-Host "Registering provider: $providerId" -ForegroundColor Cyan
    $body = $provider | ConvertTo-Json -Depth 20
    Invoke-RestMethod -Uri "$BaseUrl/admin/feed-providers" -Method Post -Headers $headers -ContentType 'application/json; charset=utf-8' -Body $body -TimeoutSec 10 | Out-Null

    if ($RegisterOnly.IsPresent) {
      $successCount += 1
      continue
    }

    Write-Host "Syncing provider: $providerId" -ForegroundColor Cyan
    $result = Invoke-RestMethod -Uri "$BaseUrl/admin/feed-providers/$providerId/sync?timeout_seconds=$TimeoutSeconds" -Method Post -Headers $headers -TimeoutSec ($TimeoutSeconds + 10)
    $totalImported += [int]$result.importedCount
    $successCount += 1
    Write-Host "Imported: $($result.importedCount), total deals: $($result.dealCount)" -ForegroundColor Green
  } catch {
    $failedCount += 1
    Write-Host "FAILED provider: $providerId" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
  }
}

if ($RegisterOnly.IsPresent) {
  Write-Host "Stage 51 provider registration completed. Success: $successCount, failed: $failedCount. Sync was skipped because -RegisterOnly was used." -ForegroundColor Green
} else {
  Write-Host "Stage 51 eBay expansion sync completed. Success: $successCount, failed: $failedCount, imported/updated deals reported by providers: $totalImported" -ForegroundColor Green
}

if ($failedCount -gt 0) {
  exit 1
}
