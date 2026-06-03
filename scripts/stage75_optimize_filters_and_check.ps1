param(
  [string]$ApiBaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

Write-Host "== DiscountHub Stage 75: live filter performance check =="
Write-Host "API: $ApiBaseUrl"
Write-Host ""

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$backendRoot = Join-Path $root "backend"

Write-Host "[1/3] Preparing SQLite performance columns and indexes"
Push-Location $backendRoot
try {
  $oldPythonPath = $env:PYTHONPATH
  $env:PYTHONPATH = (Get-Location).Path
  python -c "from app.db.database import initialize_database; initialize_database(); print('SQLite performance columns/indexes: ready')"
  $env:PYTHONPATH = $oldPythonPath
} finally {
  Pop-Location
}

Write-Host ""
Write-Host "[2/3] Backend health"
try {
  $health = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/health" -TimeoutSec 10
  Write-Host "Backend health: $($health.status) ($($health.service))"
} catch {
  Write-Warning "Backend is not running yet. Start/restart backend, then re-run this script for timings."
  return
}

function Measure-ApiGet($Name, $Url) {
  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  $result = Invoke-RestMethod -Method Get -Uri $Url -TimeoutSec 30
  $sw.Stop()
  $ms = [math]::Round($sw.Elapsed.TotalMilliseconds)
  Write-Host ("{0,-34} {1,6} ms" -f $Name, $ms)
  return $result
}

Write-Host ""
Write-Host "[3/3] API timings"
$facets1 = Measure-ApiGet "facets cold/warm #1" "$ApiBaseUrl/deals/facets"
$facets2 = Measure-ApiGet "facets cached #2" "$ApiBaseUrl/deals/facets"
$all = Measure-ApiGet "deals first page" "$ApiBaseUrl/deals?page_size=36&sort=discount_desc"
$ali = Measure-ApiGet "AliExpress page" "$ApiBaseUrl/deals?platform=AliExpress&page_size=36&sort=discount_desc"
$ebay = Measure-ApiGet "eBay page" "$ApiBaseUrl/deals?platform=eBay&page_size=36&sort=discount_desc"

Write-Host ""
Write-Host "Totals:"
Write-Host "Facets total: $($facets2.total)"
Write-Host "All page total: $($all.total)"
Write-Host "AliExpress total: $($ali.total)"
Write-Host "eBay total: $($ebay.total)"
Write-Host ""
Write-Host "Stage 75 check completed. If facets cached #2 is much faster than #1 and filtered pages are responsive, the optimization is active."
