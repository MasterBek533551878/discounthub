param(
  [string]$BindHost = "127.0.0.1",
  [int]$Port = 8000,
  [switch]$NoReload
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptRoot "..")
$BackendRoot = Join-Path $ProjectRoot "backend"

if (-not (Test-Path $BackendRoot)) {
  throw "Backend folder not found: $BackendRoot"
}

$activate = Join-Path $BackendRoot ".venv\Scripts\Activate.ps1"

Push-Location $BackendRoot
try {
  if (Test-Path $activate) {
    . $activate
  } else {
    Write-Warning "backend\.venv was not found. Using current Python from PATH."
  }

  $env:PYTHONPATH = (Get-Location).Path

  Write-Host "== DiscountHub backend ==" -ForegroundColor Cyan
  Write-Host "Root: $BackendRoot"
  Write-Host "URL : http://$BindHost`:$Port"
  Write-Host "Stop: Ctrl+C"
  Write-Host ""

  $uvicornArgs = @("app.main:app", "--host", $BindHost, "--port", "$Port")
  if (-not $NoReload) {
    $uvicornArgs += "--reload"
  }

  python -m uvicorn @uvicornArgs
} finally {
  Pop-Location
}
