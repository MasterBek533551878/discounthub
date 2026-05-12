param(
  [Parameter(Mandatory = $true)]
  [string]$Id
)

$ErrorActionPreference = "Stop"

$catalogPath = Join-Path $PSScriptRoot "..\config\provider_network_catalog.json"
$catalog = Get-Content $catalogPath -Raw | ConvertFrom-Json
$network = $catalog.networks | Where-Object { $_.id -eq $Id } | Select-Object -First 1

if ($null -eq $network) {
  throw "Provider not found in catalog: $Id"
}

foreach ($url in $network.docs) {
  Write-Host "Opening $url"
  Start-Process $url
}
