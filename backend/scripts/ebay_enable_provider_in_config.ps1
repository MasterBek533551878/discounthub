param(
  [string]$Id = 'ebay_browse_headphones',
  [bool]$Enabled = $true,
  [string]$ConfigPath = "$PSScriptRoot\..\config\feed_providers.json"
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $ConfigPath)) {
  throw "Config not found: $ConfigPath"
}

$providers = @(Get-Content $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json)
$found = $false
foreach ($provider in $providers) {
  if ($provider.id -eq $Id) {
    $enabledProperty = $provider.PSObject.Properties['enabled']
    if ($null -eq $enabledProperty) {
      $provider | Add-Member -NotePropertyName 'enabled' -NotePropertyValue $Enabled -Force
    } else {
      $provider.enabled = $Enabled
    }
    $found = $true
  }
}

if (-not $found) {
  throw "Provider not found in config: $Id"
}

$providers | ConvertTo-Json -Depth 20 | Set-Content -Path $ConfigPath -Encoding UTF8
Write-Host "Provider '$Id' enabled=$Enabled in config:" -ForegroundColor Green
Write-Host "  $ConfigPath"
Write-Host 'Restart backend or run provider_sync_from_config.ps1 to register updated config.' -ForegroundColor Yellow
