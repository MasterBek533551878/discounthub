param(
  [string]$BaseUrl = 'http://127.0.0.1:8000',
  [string]$AdminToken = 'dev-local-admin-token',
  [string]$ConfigPath = "$PSScriptRoot\..\config\feed_providers.json",
  [int]$TimeoutSeconds = 20,
  [int]$WaitSeconds = 20
)

$ErrorActionPreference = 'Stop'

function Get-ProviderListFromJson {
  param([Parameter(Mandatory = $true)] $LoadedJson)

  $result = New-Object System.Collections.Generic.List[object]

  if ($LoadedJson -is [System.Array]) {
    $candidates = @($LoadedJson)
  } elseif ($null -ne $LoadedJson.PSObject.Properties['providers']) {
    $candidates = @($LoadedJson.providers)
  } else {
    throw 'Feed provider config must be either a flat array or an object with providers array.'
  }

  foreach ($item in $candidates) {
    if ($null -eq $item) {
      continue
    }

    # Legacy recovery: earlier config could be [{ providers: [...] }, { id: ... }].
    if (($null -eq $item.PSObject.Properties['id']) -and ($null -ne $item.PSObject.Properties['providers'])) {
      foreach ($nested in @($item.providers)) {
        if ($null -ne $nested) {
          $result.Add($nested) | Out-Null
        }
      }
      continue
    }

    $result.Add($item) | Out-Null
  }

  return @($result.ToArray())
}

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

  throw "Backend is not reachable at $Url. Check the 'DiscountHub backend :8000' window and fix the startup error first."
}

if (-not (Test-Path $ConfigPath)) {
  throw "Config file not found: $ConfigPath"
}

$loaded = Get-Content $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
$providers = @(Get-ProviderListFromJson -LoadedJson $loaded)
if ($providers.Count -eq 0) {
  Write-Host 'No providers found in config.' -ForegroundColor Yellow
  exit 0
}

Wait-BackendReady -Url $BaseUrl -Seconds $WaitSeconds

$headers = @{ 'X-Admin-Token' = $AdminToken }

foreach ($provider in $providers) {
  if ($null -eq $provider.PSObject.Properties['id'] -or [string]::IsNullOrWhiteSpace([string]$provider.id)) {
    Write-Host 'Skipping malformed provider without id.' -ForegroundColor Yellow
    continue
  }

  if ($provider.enabled -eq $false) {
    Write-Host "Skipping disabled provider: $($provider.id)"
    continue
  }

  Write-Host "Registering provider: $($provider.id)" -ForegroundColor Cyan
  $body = $provider | ConvertTo-Json -Depth 20
  Invoke-RestMethod -Uri "$BaseUrl/admin/feed-providers" -Method Post -Headers $headers -ContentType 'application/json' -Body $body | Out-Null

  Write-Host "Syncing provider: $($provider.id)" -ForegroundColor Cyan
  Invoke-RestMethod -Uri "$BaseUrl/admin/feed-providers/$($provider.id)/sync?timeout_seconds=$TimeoutSeconds" -Method Post -Headers $headers
}
