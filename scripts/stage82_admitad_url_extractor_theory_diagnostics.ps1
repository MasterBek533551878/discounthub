param(
  [string]$Server = "ubuntu@51.68.46.242",
  [string[]]$ProviderIds = @("admitad_20881_alibaba_ww_v1", "admitad_6115_aliexpress_ww_v1"),
  [int]$MaxRows = 500,
  [int]$TimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$helper = Join-Path $scriptDir "stage82_admitad_url_extractor_theory_diagnostics.py"
if (-not (Test-Path $helper)) {
  throw "Helper script not found: $helper"
}

Write-Host "== DiscountHub Stage 82: Admitad URL extractor theory diagnostics =="
Write-Host "Server: $Server"
Write-Host "Providers: $($ProviderIds -join ', ')"
Write-Host "Max rows/provider: $MaxRows"
Write-Host "Mode: dry-run only; no import, no delete"
Write-Host ""

Write-Host "[1/2] Upload helper script"
scp $helper "$Server`:/tmp/stage82_admitad_url_extractor_theory_diagnostics.py"

$ids = ($ProviderIds -join ",")
Write-Host "[2/2] Run diagnostics on server"
ssh $Server "cd /opt/discounthub/backend && source .venv/bin/activate && python /tmp/stage82_admitad_url_extractor_theory_diagnostics.py --provider-ids '$ids' --max-rows $MaxRows --timeout $TimeoutSeconds"

Write-Host ""
Write-Host "Stage 82 diagnostics completed."
