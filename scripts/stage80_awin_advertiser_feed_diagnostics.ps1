param(
  [string]$EnvPath = "backend/.env",
  [int]$MaxFeeds = 25,
  [int]$MaxRows = 200,
  [int]$MinDiscountPercent = 10,
  [int]$TimeoutSeconds = 30,
  [switch]$IncludeNotJoined
)

$ErrorActionPreference = "Stop"

$pythonCandidates = @(
  "backend\.venv\Scripts\python.exe",
  "py"
)

$python = $null
foreach ($candidate in $pythonCandidates) {
  if ($candidate -eq "py") {
    try {
      & py -3 --version *> $null
      if ($LASTEXITCODE -eq 0) { $python = "py"; break }
    } catch {}
  } elseif (Test-Path $candidate) {
    $python = $candidate
    break
  }
}

if (-not $python) {
  throw "Python was not found. Install Python or restore backend/.venv."
}

$argsList = @()
if ($python -eq "py") { $argsList += "-3" }
$argsList += @(
  "scripts/stage80_awin_advertiser_feed_diagnostics.py",
  "--env", $EnvPath,
  "--max-feeds", "$MaxFeeds",
  "--max-rows", "$MaxRows",
  "--min-discount", "$MinDiscountPercent",
  "--timeout", "$TimeoutSeconds"
)
if ($IncludeNotJoined) { $argsList += "--include-not-joined" }

& $python @argsList
if ($LASTEXITCODE -ne 0) {
  throw "Stage 80 Awin diagnostics failed with exit code $LASTEXITCODE"
}
