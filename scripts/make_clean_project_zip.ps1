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
  ".vscode/",
  ".dart_tool/",
  ".gradle/",
  "build/",
  "coverage/",
  "backend/.venv/",
  "backend/data/",
  "backend/exports/",
  "backend/logs/",
  "android/.gradle/",
  "android/app/build/",
  "ios/build/",
  "ios/Pods/",
  "linux/build/",
  "macos/build/",
  "windows/build/"
)

$excludeExactFiles = @(
  ".flutter-plugins-dependencies",
  ".metadata",
  ".packages",
  "android/key.properties",
  "android/local.properties",
  "lib.zip"
)

$excludeExtensions = @(
  ".zip",
  ".sqlite",
  ".sqlite3",
  ".db",
  ".db-shm",
  ".db-wal",
  ".pyc",
  ".pyo",
  ".jks",
  ".keystore",
  ".p8",
  ".iml"
)

function Test-ExcludedFile($RelativePath, $Extension, $LeafName) {
  $normalized = $RelativePath.Replace('\', '/')
  $lower = $normalized.ToLowerInvariant()
  $leafLower = $LeafName.ToLowerInvariant()

  foreach ($dir in $excludeDirPatterns) {
    if ($lower.StartsWith($dir.ToLowerInvariant())) {
      return $true
    }
  }

  foreach ($file in $excludeExactFiles) {
    if ($lower.Equals($file.ToLowerInvariant())) {
      return $true
    }
  }

  if ($leafLower -eq ".env" -or $leafLower.StartsWith(".env.")) {
    if ($leafLower -ne ".env.example" -and $leafLower -ne ".env.production.example") {
      return $true
    }
  }

  foreach ($ext in $excludeExtensions) {
    if ($Extension.Equals($ext, [System.StringComparison]::OrdinalIgnoreCase)) {
      return $true
    }
  }

  if ($lower.Contains("/__pycache__/")) {
    return $true
  }

  return $false
}

try {
  New-Item -ItemType Directory -Force -Path $TempRoot | Out-Null

  Get-ChildItem -Path $ProjectRootPath -Recurse -File -Force | ForEach-Object {
    $relative = $_.FullName.Substring($ProjectRootPath.Length + 1)
    if (Test-ExcludedFile -RelativePath $relative -Extension $_.Extension -LeafName $_.Name) {
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
