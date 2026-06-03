param(
  [string]$ApiBaseUrl = "http://127.0.0.1:8000",
  [string]$DbPath = "backend/data/discounthub.sqlite3",
  [int]$MinDiscountPercent = 1
)

$ErrorActionPreference = "Stop"

function Resolve-PythonExecutable {
  $localPython = Join-Path (Get-Location) "backend\.venv\Scripts\python.exe"
  if (Test-Path $localPython) { return $localPython }

  $commands = @("python", "py")
  foreach ($command in $commands) {
    $found = Get-Command $command -ErrorAction SilentlyContinue
    if ($found) { return $found.Source }
  }

  throw "Python executable not found. Expected backend\.venv\Scripts\python.exe or python in PATH."
}

function Invoke-Json {
  param([string]$Uri, [int]$TimeoutSec = 30)
  return Invoke-RestMethod -Method Get -Uri $Uri -TimeoutSec $TimeoutSec
}

if ($MinDiscountPercent -lt 1) { $MinDiscountPercent = 1 }

Write-Host "== DiscountHub Stage 63: fix filter counts + clean non-discounts =="
Write-Host "API: $ApiBaseUrl"
Write-Host "DB : $DbPath"
Write-Host "MinDiscountPercent: $MinDiscountPercent"
Write-Host ""

$health = Invoke-Json -Uri "$ApiBaseUrl/health" -TimeoutSec 10
Write-Host "Backend health before cleanup: $($health.status) ($($health.service))"

if (!(Test-Path $DbPath)) { throw "SQLite DB not found: $DbPath" }
$pythonExe = Resolve-PythonExecutable
Write-Host "Python: $pythonExe"

$env:DISCOUNTHUB_DB_PATH = (Resolve-Path $DbPath).Path
$env:DISCOUNTHUB_MIN_DISCOUNT = [string]$MinDiscountPercent
& $pythonExe scripts\stage63_clean_discount_inventory.py

Write-Host ""
Write-Host "Now restart backend after applying Stage 63 code changes if it is already running."
Write-Host "After restart, run: .\scripts\stage63_check_filter_counts.ps1 -ApiBaseUrl `"$ApiBaseUrl`""
