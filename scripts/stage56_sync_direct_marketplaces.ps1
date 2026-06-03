param(
  [string]$ApiBaseUrl = "http://127.0.0.1:8000",
  [string]$AdminToken = "dev-local-admin-token",
  [string]$ConfigPath = "backend/config/stage56_direct_marketplace_providers.json",
  [int]$TimeoutSeconds = 30,
  [int]$MaxProviders = 0
)

$ErrorActionPreference = "Stop"

function Get-HttpErrorDetail {
  param($ErrorRecord)

  $message = $ErrorRecord.Exception.Message
  $response = $ErrorRecord.Exception.Response
  if ($null -eq $response) {
    return $message
  }

  try {
    $stream = $response.GetResponseStream()
    if ($null -eq $stream) {
      return $message
    }
    $reader = New-Object System.IO.StreamReader($stream)
    $body = $reader.ReadToEnd()
    if (![string]::IsNullOrWhiteSpace($body)) {
      return "$message :: $body"
    }
  } catch {
    return $message
  }

  return $message
}


function Read-ProviderConfigArray {
  param([string]$Path)

  if (!(Test-Path $Path)) {
    throw "Provider config was not found: $Path"
  }

  $raw = Get-Content -Path $Path -Raw -Encoding UTF8
  $parsed = ConvertFrom-Json -InputObject $raw

  # Windows PowerShell can keep a top-level JSON array as one array object.
  # Force enumeration so foreach receives one provider at a time.
  if ($parsed -is [System.Array]) {
    return @($parsed)
  }

  return @($parsed | ForEach-Object { $_ })
}

Write-Host "== DiscountHub Stage 56 direct marketplace sync =="
Write-Host "API: $ApiBaseUrl"
Write-Host "Config: $ConfigPath"
Write-Host ""

$headers = @{ "X-Admin-Token" = $AdminToken }
$providers = @(Read-ProviderConfigArray -Path $ConfigPath)
if ($MaxProviders -gt 0) {
  $providers = @($providers | Select-Object -First $MaxProviders)
}

$totalBefore = (Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals/facets").total
Write-Host "Deals before: $totalBefore"
Write-Host "Providers to sync: $($providers.Count)"
Write-Host ""

$importedTotal = 0
$failed = @()
$index = 0

foreach ($provider in $providers) {
  $index += 1
  $id = [string]$provider.id
  Write-Host "[$index/$($providers.Count)] Syncing $id"
  try {
    $sync = Invoke-RestMethod -Method Post -Uri "$ApiBaseUrl/admin/feed-providers/$id/sync?timeout_seconds=$TimeoutSeconds" -Headers $headers
    $importedTotal += [int]$sync.importedCount
    Write-Host ("  Status={0}; imported={1}; total={2}" -f $sync.status, $sync.importedCount, $sync.dealCount)
  } catch {
    $message = Get-HttpErrorDetail $_
    $failed += "$id -> $message"
    Write-Warning "  Failed: $message"
  }
}

Write-Host ""
$totalAfter = (Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals/facets").total
Write-Host "Imported total reported: $importedTotal"
Write-Host "Deals after: $totalAfter"
Write-Host "Delta visible facets total: $($totalAfter - $totalBefore)"

$facets = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals/facets"
Write-Host ""
Write-Host "Marketplaces:"
$facets.marketplaces | Select-Object -First 20 | ForEach-Object {
  Write-Host ("  {0}: {1}" -f $_.id, $_.count)
}

if ($failed.Count -gt 0) {
  Write-Host ""
  Write-Warning "Failures:"
  $failed | ForEach-Object { Write-Warning $_ }
  exit 1
}

Write-Host "Stage 56 sync completed."
