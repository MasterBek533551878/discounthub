param(
  [string]$OutputPath = "$env:USERPROFILE\Downloads\discounthub_clean.zip"
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptRoot "..")
$ProjectRootPath = $ProjectRoot.Path

Write-Host "== DiscountHub Stage 59: clean release package check ==" -ForegroundColor Cyan
Write-Host "Project: $ProjectRootPath"
Write-Host "Output : $OutputPath"
Write-Host ""

$makeZip = Join-Path $ScriptRoot "make_clean_project_zip.ps1"
if (-not (Test-Path $makeZip)) {
  throw "Missing script: scripts\make_clean_project_zip.ps1"
}

& $makeZip -OutputPath $OutputPath

Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead($OutputPath)
try {
  $entries = @($zip.Entries | ForEach-Object { $_.FullName.Replace('\\', '/') })
  $bad = New-Object System.Collections.Generic.List[string]

  foreach ($entry in $entries) {
    $lower = $entry.ToLowerInvariant()
    if ($lower -match '(^|/)\.git/' -or
        $lower -match '(^|/)\.dart_tool/' -or
        $lower -match '(^|/)build/' -or
        $lower -match '^backend/\.venv/' -or
        $lower -match '^backend/data/' -or
        $lower -match '^backend/exports/' -or
        $lower -match '^backend/logs/' -or
        $lower -eq '.env' -or
        $lower -match '(^|/)\.env(\.|$)' -or
        $lower -eq 'backend/.env' -or
        $lower -match '^backend/\.env\.' -or
        $lower -eq 'android/key.properties' -or
        $lower -eq 'android/local.properties' -or
        $lower -match '\.(sqlite|sqlite3|db|jks|keystore|p8|zip)$') {
      if (-not ($lower.EndsWith('.env.example') -or $lower.EndsWith('.env.production.example'))) {
        $bad.Add($entry) | Out-Null
      }
    }
  }

  Write-Host "ZIP entries: $($entries.Count)"
  Write-Host "ZIP size   : $([Math]::Round((Get-Item $OutputPath).Length / 1MB, 2)) MB"

  if ($bad.Count -gt 0) {
    Write-Host ""
    Write-Host "Forbidden files found in clean ZIP:" -ForegroundColor Red
    $bad | Select-Object -First 80 | ForEach-Object { Write-Host " - $_" -ForegroundColor Red }
    if ($bad.Count -gt 80) { Write-Host " ... plus $($bad.Count - 80) more" -ForegroundColor Red }
    throw "Clean ZIP check failed."
  }

  Write-Host "Forbidden files: 0" -ForegroundColor Green
  Write-Host "Clean release ZIP looks safe." -ForegroundColor Green
} finally {
  $zip.Dispose()
}
