param(
  [Parameter(Mandatory=$true)]
  [string]$Id,

  [string]$ConfigPath = "$PSScriptRoot\..\config\feed_providers.json"
)

if (-not (Test-Path $ConfigPath)) {
  Write-Error "Provider config not found: $ConfigPath"
  exit 1
}

try {
  $raw = Get-Content $ConfigPath -Raw -Encoding UTF8
  if ([string]::IsNullOrWhiteSpace($raw)) {
    Write-Error "Provider config is empty: $ConfigPath"
    exit 1
  }

  $json = $raw | ConvertFrom-Json
  $providers = @()

  if ($json -is [System.Array]) {
    $providers = @($json)
  } elseif ($json.providers) {
    $providers = @($json.providers)
  } else {
    Write-Error "Unsupported provider config shape. Expected array or object with 'providers'."
    exit 1
  }

  $before = $providers.Count
  $nextProviders = @($providers | Where-Object { $_.id -ne $Id })
  $after = $nextProviders.Count

  if ($before -eq $after) {
    Write-Host "Provider not found in config: $Id"
    exit 0
  }

  if ($json -is [System.Array]) {
    $output = $nextProviders
  } else {
    $json.providers = $nextProviders
    $output = $json
  }

  $output |
    ConvertTo-Json -Depth 20 |
    Set-Content -Path $ConfigPath -Encoding UTF8

  Write-Host "Provider removed from config:"
  Write-Host "  $Id"
  Write-Host "Config:"
  Write-Host "  $ConfigPath"
} catch {
  Write-Error $_
  exit 1
}
