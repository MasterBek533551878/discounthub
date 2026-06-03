param(
  [string]$ApiBaseUrl = "http://127.0.0.1:8000",
  [string]$AdminToken = "dev-local-admin-token",
  [string]$ConfigPath = "backend/config/stage56_direct_marketplace_providers.json",
  [switch]$SyncAfterRegister,
  [int]$TimeoutSeconds = 30
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

Write-Host "== DiscountHub Stage 56 direct marketplace registration =="
Write-Host "API: $ApiBaseUrl"
Write-Host "Config: $ConfigPath"
Write-Host ""

$health = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/health"
Write-Host "Health: $($health.status) ($($health.service))"

$providers = @(Read-ProviderConfigArray -Path $ConfigPath)
if ($null -eq $providers -or $providers.Count -eq 0) {
  throw "No providers were found in $ConfigPath"
}

$headers = @{ "X-Admin-Token" = $AdminToken }
$registered = 0
$synced = 0
$failed = @()

foreach ($provider in $providers) {
  $id = [string]$provider.id
  try {
    $body = $provider | ConvertTo-Json -Depth 8
    $result = Invoke-RestMethod -Method Post -Uri "$ApiBaseUrl/admin/feed-providers" -Headers $headers -ContentType "application/json" -Body $body
    $registered += 1
    Write-Host ("Registered: {0} [{1}] mode={2}" -f $result.id, $result.adapter, $result.monetizationMode)

    if ($SyncAfterRegister) {
      $sync = Invoke-RestMethod -Method Post -Uri "$ApiBaseUrl/admin/feed-providers/$id/sync?timeout_seconds=$TimeoutSeconds" -Headers $headers
      $synced += 1
      Write-Host ("  Synced: {0}, imported={1}, total={2}" -f $sync.status, $sync.importedCount, $sync.dealCount)
    }
  } catch {
    $message = Get-HttpErrorDetail $_
    $failed += "$id -> $message"
    Write-Warning "Failed: $id -> $message"
  }
}

Write-Host ""
Write-Host "Registered: $registered / $($providers.Count)"
if ($SyncAfterRegister) {
  Write-Host "Synced: $synced / $($providers.Count)"
}

if ($failed.Count -gt 0) {
  Write-Host ""
  Write-Warning "Failures:"
  $failed | ForEach-Object { Write-Warning $_ }
  exit 1
}

Write-Host "Stage 56 registration completed."
