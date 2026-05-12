$ErrorActionPreference = "Stop"

$catalogPath = Join-Path $PSScriptRoot "..\config\provider_network_catalog.json"
if (!(Test-Path $catalogPath)) {
  throw "Catalog not found: $catalogPath"
}

$catalog = Get-Content $catalogPath -Raw | ConvertFrom-Json
$catalog.networks |
  Sort-Object priority |
  Select-Object priority, id, name, status, sourceType, adapterTarget |
  Format-Table -AutoSize
