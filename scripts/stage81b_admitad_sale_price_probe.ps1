param(
  [string]$Server = "ubuntu@51.68.46.242",
  [string]$ProviderId = "admitad_20881_alibaba_ww_v1",
  [int]$MaxRows = 25000,
  [int]$TimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$helper = Join-Path $PSScriptRoot "stage81b_admitad_sale_price_probe.py"
$remote = "/tmp/stage81b_admitad_sale_price_probe.py"

Write-Host "== DiscountHub Stage 81b: Admitad sale_price probe =="
Write-Host "Server: $Server"
Write-Host "Provider: $ProviderId"
Write-Host "Max rows: $MaxRows"
Write-Host "Mode: dry-run only; no import, no delete"
Write-Host ""

if (!(Test-Path $helper)) {
  throw "Helper script not found: $helper"
}

Write-Host "[1/2] Upload helper script"
scp $helper "${Server}:$remote"

Write-Host "[2/2] Run probe on server"
ssh $Server "python3 $remote --db /opt/discounthub/backend/data/discounthub.sqlite3 --provider-id '$ProviderId' --max-rows $MaxRows --timeout $TimeoutSeconds"

Write-Host ""
Write-Host "Stage 81b probe completed."
