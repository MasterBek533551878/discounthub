param(
  [Parameter(Mandatory=$true)]
  [string]$AppIconSource,

  [Parameter(Mandatory=$false)]
  [string]$LogoFullSource,

  [Parameter(Mandatory=$false)]
  [string]$BackgroundColor = "#0B63FF"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path ".").Path
$ScriptPath = Join-Path $ProjectRoot "scripts\generate_brand_icons.py"

if (-not (Test-Path $ScriptPath)) {
  throw "Script not found: $ScriptPath. Run this command from the Flutter project root."
}

if (-not (Test-Path $AppIconSource)) {
  throw "App icon source not found: $AppIconSource"
}

$Python = $null
foreach ($candidate in @("py", "python", "python3")) {
  try {
    & $candidate --version *> $null
    if ($LASTEXITCODE -eq 0) {
      $Python = $candidate
      break
    }
  } catch {}
}

if (-not $Python) {
  throw "Python was not found. Install Python or run the icon generation script manually on a machine with Python."
}

try {
  & $Python -c "import PIL" *> $null
} catch {
  Write-Host "Pillow is missing. Installing Pillow..." -ForegroundColor Yellow
  & $Python -m pip install pillow
}

$Args = @(
  $ScriptPath,
  "--project-root", $ProjectRoot,
  "--app-icon-source", (Resolve-Path $AppIconSource).Path,
  "--background-color", $BackgroundColor
)

if ($LogoFullSource -and (Test-Path $LogoFullSource)) {
  $Args += @("--logo-full-source", (Resolve-Path $LogoFullSource).Path)
}

& $Python @Args

Write-Host ""
Write-Host "Done. Updated:" -ForegroundColor Green
Write-Host "- assets/brand/logo.png"
Write-Host "- Android launcher icons"
Write-Host "- iOS AppIcon set"
Write-Host "- iOS launch image"
Write-Host "- Web favicon/manifest icons"
Write-Host ""
Write-Host "Next: run flutter clean, flutter pub get, flutter analyze, then rebuild the app." -ForegroundColor Cyan
