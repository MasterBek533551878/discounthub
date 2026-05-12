param(
  [string]$OutputPath = "$env:USERPROFILE\Downloads\discounthub_clean.zip"
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptRoot "..")
$ProjectRootPath = $ProjectRoot.Path.TrimEnd('\')
$TempRoot = Join-Path $env:TEMP ("discounthub_clean_" + [Guid]::NewGuid().ToString("N"))

$excludeDirPatterns = @(
  ".git/",
  ".idea/",
  ".dart_tool/",
  "build/",
  "backend/.venv/",
  "backend/data/",
  "backend/exports/",
  "backend/logs/",
  "android/app/build/",
  "ios/Pods/"
)

$excludeFilePatterns = @(
  ".env",
  "backend/.env",
  "lib.zip"
)

$excludeExtensions = @(
  ".zip",
  ".sqlite",
  ".sqlite3",
  ".db",
  ".pyc"
)

function Test-ExcludedFile($RelativePath, $Extension) {
  $normalized = $RelativePath.Replace('\', '/')

  foreach ($dir in $excludeDirPatterns) {
    if ($normalized.StartsWith($dir, [System.StringComparison]::OrdinalIgnoreCase)) {
      return $true
    }
  }

  foreach ($file in $excludeFilePatterns) {
    if ($normalized.Equals($file, [System.StringComparison]::OrdinalIgnoreCase)) {
      return $true
    }
  }

  foreach ($ext in $excludeExtensions) {
    if ($Extension.Equals($ext, [System.StringComparison]::OrdinalIgnoreCase)) {
      return $true
    }
  }

  return $false
}

try {
  New-Item -ItemType Directory -Force -Path $TempRoot | Out-Null

  Get-ChildItem -Path $ProjectRootPath -Recurse -File | ForEach-Object {
    $relative = $_.FullName.Substring($ProjectRootPath.Length + 1)
    if (Test-ExcludedFile -RelativePath $relative -Extension $_.Extension) {
      return
    }

    $destination = Join-Path $TempRoot $relative
    $destinationDir = Split-Path -Parent $destination
    New-Item -ItemType Directory -Force -Path $destinationDir | Out-Null
    Copy-Item -Path $_.FullName -Destination $destination -Force
  }

  if (Test-Path $OutputPath) {
    Remove-Item $OutputPath -Force
  }

  Compress-Archive -Path (Join-Path $TempRoot "*") -DestinationPath $OutputPath -Force
  Write-Host "Clean ZIP created: $OutputPath" -ForegroundColor Green
} finally {
  if (Test-Path $TempRoot) {
    Remove-Item $TempRoot -Recurse -Force
  }
}
