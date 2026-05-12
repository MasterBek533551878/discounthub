param(
  [int]$Port = 9000
)

$backendRoot = Split-Path -Parent $PSScriptRoot
$examplesDir = Join-Path $backendRoot "examples"
$venvPython = Join-Path $backendRoot ".venv\Scripts\python.exe"

if (Test-Path $venvPython) {
  $pythonCmd = $venvPython
} else {
  $pythonCmd = "py"
}

if (-not (Test-Path $examplesDir)) {
  throw "Examples directory not found: $examplesDir"
}

Write-Host "Starting demo provider feed server..." -ForegroundColor Cyan
Write-Host "Directory: $examplesDir" -ForegroundColor DarkGray
Write-Host "URL: http://127.0.0.1:$Port/provider_feed.json" -ForegroundColor Green
Write-Host "Keep this PowerShell window open while syncing provider feeds." -ForegroundColor Yellow

Push-Location $examplesDir
try {
  if ($pythonCmd -eq "py") {
    & py -m http.server $Port
  } else {
    & $pythonCmd -m http.server $Port
  }
} finally {
  Pop-Location
}
