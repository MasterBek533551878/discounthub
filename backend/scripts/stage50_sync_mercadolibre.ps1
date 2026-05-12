param(
  [string]$BaseUrl = 'http://127.0.0.1:8000',
  [string]$AdminToken = 'dev-local-admin-token',
  [string]$ConfigPath = "$PSScriptRoot\..\config\feed_providers.json",
  [int]$TimeoutSeconds = 30,
  [int]$WaitSeconds = 20
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

  throw "Backend is not reachable at $Url. Start uvicorn first."
}

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
    if ($null -eq $item) { continue }
    if (($null -eq $item.PSObject.Properties['id']) -and ($null -ne $item.PSObject.Properties['providers'])) {
      foreach ($nested in @($item.providers)) {
        if ($null -ne $nested) { $result.Add($nested) | Out-Null }
      }
      continue
    }
    $result.Add($item) | Out-Null
  }

  return @($result.ToArray())
}

function Invoke-JsonPostUtf8 {
  param(
    [Parameter(Mandatory = $true)][string]$Uri,
    [Parameter(Mandatory = $true)]$Payload,
    [Parameter(Mandatory = $true)][hashtable]$Headers
  )

  $json = $Payload | ConvertTo-Json -Depth 30 -Compress
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  $bytes = $utf8NoBom.GetBytes($json)

  Invoke-RestMethod `
    -Uri $Uri `
    -Method Post `
    -Headers $Headers `
    -ContentType 'application/json; charset=utf-8' `
    -Body $bytes
}

if (-not (Test-Path $ConfigPath)) {
  throw "Config file not found: $ConfigPath"
}

Wait-BackendReady -Url $BaseUrl -Seconds $WaitSeconds

$loaded = Get-Content $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
$providers = @(Get-ProviderListFromJson -LoadedJson $loaded | Where-Object { $_.adapter -eq 'mercadolibre_search_api' -and $_.enabled -ne $false })

if ($providers.Count -eq 0) {
  Write-Host 'No enabled Mercado Libre providers found in config.' -ForegroundColor Yellow
  exit 0
}

$headers = @{ 'X-Admin-Token' = $AdminToken }
$totalImported = 0

foreach ($provider in $providers) {
  Write-Host "Registering Mercado Libre provider: $($provider.id)" -ForegroundColor Cyan

  $payload = [ordered]@{
    id = [string]$provider.id
    name = [string]$provider.name
    url = [string]$provider.url
    adapter = [string]$provider.adapter
    enabled = [bool]$provider.enabled
    replaceOnSync = [bool]$provider.replaceOnSync
  }

  Invoke-JsonPostUtf8 -Uri "$BaseUrl/admin/feed-providers" -Headers $headers -Payload $payload | Out-Null

  Write-Host "Syncing Mercado Libre provider: $($provider.id)" -ForegroundColor Cyan
  $result = Invoke-RestMethod -Uri "$BaseUrl/admin/feed-providers/$($provider.id)/sync?timeout_seconds=$TimeoutSeconds" -Method Post -Headers $headers
  $totalImported += [int]$result.importedCount
  $result
}

Write-Host "Mercado Libre sync completed. Imported/updated: $totalImported" -ForegroundColor Green
Invoke-RestMethod -Uri "$BaseUrl/storage/status" -Method Get
