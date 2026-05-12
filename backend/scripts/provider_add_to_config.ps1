param(
  [Parameter(Mandatory=$true)][string]$Id,
  [Parameter(Mandatory=$true)][string]$Name,
  [Parameter(Mandatory=$true)][string]$Url,
  [ValidateSet('auto','discounthub_json','generic_products','google_merchant','awin_products','ebay_browse_api','mercadolibre_search_api')]
  [string]$Adapter = 'auto',
  [bool]$Enabled = $true,
  [bool]$ReplaceOnSync = $false,
  [string]$ConfigPath = "$PSScriptRoot\..\config\feed_providers.json"
)

$ErrorActionPreference = 'Stop'

$resolvedPath = Resolve-Path -Path (Split-Path $ConfigPath -Parent) -ErrorAction SilentlyContinue
if (-not $resolvedPath) {
  New-Item -ItemType Directory -Path (Split-Path $ConfigPath -Parent) -Force | Out-Null
}

if (Test-Path $ConfigPath) {
  $raw = Get-Content $ConfigPath -Raw
  if ($raw.Trim().Length -eq 0) {
    $providers = @()
  } else {
    $providers = @($raw | ConvertFrom-Json)
  }
} else {
  $providers = @()
}

$newProvider = [ordered]@{
  id = $Id
  name = $Name
  url = $Url
  adapter = $Adapter
  enabled = $Enabled
  replaceOnSync = $ReplaceOnSync
}

$next = @()
$found = $false
foreach ($provider in $providers) {
  if ($provider.id -eq $Id) {
    $next += [pscustomobject]$newProvider
    $found = $true
  } else {
    $next += $provider
  }
}

if (-not $found) {
  $next += [pscustomobject]$newProvider
}

$next | ConvertTo-Json -Depth 20 | Set-Content -Path $ConfigPath -Encoding UTF8
Write-Host "Provider saved to config:" -ForegroundColor Green
Write-Host "  $ConfigPath"
Write-Host "  $Id -> $Url ($Adapter)"
