param(
  [string]$Server = "ubuntu@51.68.46.242",
  [string]$ProviderId = "admitad_6115_aliexpress_ww_v1",
  [int]$MaxRows = 20,
  [int]$TimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"

Write-Host "== DiscountHub Stage 83: AliExpress nested deeplink diagnostics =="
Write-Host "Server: $Server"
Write-Host "Provider: $ProviderId"
Write-Host "Max rows: $MaxRows"
Write-Host "Mode: dry-run only; no import, no delete"
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Helper = Join-Path $ScriptDir "stage83_aliexpress_nested_deeplink_diagnostics.py"

if (-not (Test-Path $Helper)) {
  throw "Helper script not found: $Helper"
}

Write-Host "[1/2] Upload helper script"
scp $Helper "$Server`:/tmp/stage83_aliexpress_nested_deeplink_diagnostics.py"

Write-Host "[2/2] Run diagnostics on server"
$remote = "python3 /tmp/stage83_aliexpress_nested_deeplink_diagnostics.py --provider-id '$ProviderId' --max-rows $MaxRows --timeout $TimeoutSeconds"
ssh $Server $remote

Write-Host ""
Write-Host "Stage 83 diagnostics completed."
