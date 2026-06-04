param(
  [string]$Server = "ubuntu@51.68.46.242",
  [string]$ProviderId = "admitad_20881_alibaba_ww_v1",
  [int]$MaxRows = 25000,
  [int]$TimeoutSeconds = 30,
  [string]$RemoteBackendDir = "/opt/discounthub/backend"
)

$ErrorActionPreference = "Stop"

Write-Host "== DiscountHub Stage 81: Admitad provider discount diagnostics =="
Write-Host "Server: $Server"
Write-Host "Provider: $ProviderId"
Write-Host "Max rows: $MaxRows"
Write-Host "Mode: dry-run only; no import, no delete"
Write-Host ""

$LocalScript = Join-Path $PSScriptRoot "stage81_admitad_provider_discount_diagnostics.py"
if (-not (Test-Path $LocalScript)) {
  throw "Missing helper script: $LocalScript"
}

$RemoteScript = "/tmp/stage81_admitad_provider_discount_diagnostics.py"

Write-Host "[1/2] Upload helper script"
scp $LocalScript "${Server}:$RemoteScript"

Write-Host "[2/2] Run diagnostics on server"
$remoteCommand = "cd $RemoteBackendDir && python3 $RemoteScript --provider-id '$ProviderId' --max-rows $MaxRows --timeout $TimeoutSeconds"
ssh $Server $remoteCommand

Write-Host ""
Write-Host "Stage 81 diagnostics completed."
