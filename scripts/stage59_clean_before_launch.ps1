param(
  [switch]$Apply,
  [switch]$ClearClickEvents,
  [switch]$RemoveOldDbBackups
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptRoot "..")
$ProjectRootPath = $ProjectRoot.Path

function Write-Step([string]$Text) {
  Write-Host ""
  Write-Host $Text -ForegroundColor Cyan
}

function Remove-SafePath([string]$RelativePath) {
  $path = Join-Path $ProjectRootPath $RelativePath
  if (Test-Path $path) {
    if ($Apply) {
      Remove-Item -Path $path -Recurse -Force
      Write-Host "Removed: $RelativePath" -ForegroundColor Green
    } else {
      Write-Host "Would remove: $RelativePath" -ForegroundColor Yellow
    }
  }
}

function Remove-SafeFile([System.IO.FileInfo]$File) {
  $relative = $File.FullName.Substring($ProjectRootPath.Length + 1)
  if ($Apply) {
    Remove-Item -Path $File.FullName -Force
    Write-Host "Removed file: $relative" -ForegroundColor Green
  } else {
    Write-Host "Would remove file: $relative" -ForegroundColor Yellow
  }
}

Write-Host "== DiscountHub Stage 59: clean before launch ==" -ForegroundColor Cyan
Write-Host "Project: $ProjectRootPath"
if ($Apply) {
  Write-Host "Mode: APPLY" -ForegroundColor Green
} else {
  Write-Host "Mode: DRY RUN. Nothing will be deleted. Add -Apply to clean." -ForegroundColor Yellow
}

Write-Step "[1/5] Removing generated Flutter/IDE/build caches"
$generatedDirs = @(
  ".dart_tool",
  "build",
  "coverage",
  ".pytest_cache",
  ".mypy_cache",
  ".ruff_cache",
  "backend\.pytest_cache",
  "backend\.mypy_cache",
  "backend\.ruff_cache",
  "backend\logs",
  "backend\exports",
  "android\.gradle",
  "android\app\build",
  "ios\build",
  "ios\Pods",
  "macos\build",
  "linux\build",
  "windows\build"
)
foreach ($dir in $generatedDirs) { Remove-SafePath $dir }

Write-Step "[2/5] Removing Python cache files"
Get-ChildItem -Path $ProjectRootPath -Recurse -Directory -Force -Filter "__pycache__" -ErrorAction SilentlyContinue | ForEach-Object {
  $relative = $_.FullName.Substring($ProjectRootPath.Length + 1)
  if ($Apply) {
    Remove-Item -Path $_.FullName -Recurse -Force
    Write-Host "Removed dir: $relative" -ForegroundColor Green
  } else {
    Write-Host "Would remove dir: $relative" -ForegroundColor Yellow
  }
}
Get-ChildItem -Path $ProjectRootPath -Recurse -File -Force -Include "*.pyc", "*.pyo" -ErrorAction SilentlyContinue | ForEach-Object { Remove-SafeFile $_ }

Write-Step "[3/5] Removing local ZIP artifacts inside project folder"
Get-ChildItem -Path $ProjectRootPath -Recurse -File -Force -Include "*.zip" -ErrorAction SilentlyContinue | ForEach-Object { Remove-SafeFile $_ }

if ($RemoveOldDbBackups) {
  Write-Step "[4/5] Removing old SQLite backup files"
  $dataDir = Join-Path $ProjectRootPath "backend\data"
  if (Test-Path $dataDir) {
    Get-ChildItem -Path $dataDir -File -Force -ErrorAction SilentlyContinue | Where-Object {
      $_.Name -match "\.stage\d+_backup_" -or $_.Name -match "\.backup" -or $_.Name -match "\.bak$"
    } | ForEach-Object { Remove-SafeFile $_ }
  }
} else {
  Write-Step "[4/5] Skipping old SQLite backup deletion"
  Write-Host "Use -RemoveOldDbBackups if you want to delete old backend/data/*.stage*_backup_* files." -ForegroundColor DarkYellow
}

Write-Step "[5/5] Cleaning runtime database garbage"
$dbPath = Join-Path $ProjectRootPath "backend\data\discounthub.sqlite3"
if (-not (Test-Path $dbPath)) {
  Write-Host "SQLite DB not found, skipping DB cleanup: $dbPath" -ForegroundColor DarkYellow
} elseif (-not $Apply) {
  Write-Host "Would backup and clean DB: backend\data\discounthub.sqlite3" -ForegroundColor Yellow
  Write-Host "Would remove old MercadoLibre providers/deals/sync runs." -ForegroundColor Yellow
  if ($ClearClickEvents) { Write-Host "Would clear click_events." -ForegroundColor Yellow }
} else {
  $tmpScript = Join-Path $env:TEMP ("discounthub_stage59_db_cleanup_" + [Guid]::NewGuid().ToString("N") + ".py")
  $clearClicksArg = "0"
  if ($ClearClickEvents) { $clearClicksArg = "1" }

  $pythonCode = @'
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DB = Path(sys.argv[1])
CLEAR_CLICKS = sys.argv[2] == "1"

if not DB.exists():
    raise SystemExit(f"DB not found: {DB}")

ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
backup = DB.with_name(DB.name + f".stage59_backup_{ts}")
shutil.copy2(DB, backup)

con = sqlite3.connect(DB)
try:
    cur = con.cursor()
    def count(table, where="1=1"):
        return cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}").fetchone()[0]

    before = {
        "deals": count("deals"),
        "providers": count("feed_providers"),
        "runs": count("feed_sync_runs"),
        "clicks": count("click_events") if cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='click_events'").fetchone() else 0,
    }

    cur.execute("""
        DELETE FROM deals
        WHERE lower(coalesce(provider_id, '')) LIKE 'mercadolibre_%'
           OR lower(coalesce(platform, '')) LIKE '%mercado%'
    """)
    deleted_deals = cur.rowcount

    cur.execute("""
        DELETE FROM feed_sync_runs
        WHERE lower(coalesce(provider_id, '')) LIKE 'mercadolibre_%'
           OR lower(coalesce(provider_name, '')) LIKE '%mercado%'
    """)
    deleted_runs = cur.rowcount

    cur.execute("""
        DELETE FROM feed_providers
        WHERE lower(coalesce(id, '')) LIKE 'mercadolibre_%'
           OR lower(coalesce(name, '')) LIKE '%mercado%'
    """)
    deleted_providers = cur.rowcount

    deleted_clicks = 0
    if CLEAR_CLICKS and cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='click_events'").fetchone():
        cur.execute("DELETE FROM click_events")
        deleted_clicks = cur.rowcount

    con.commit()
    cur.execute("VACUUM")

    after = {
        "deals": count("deals"),
        "providers": count("feed_providers"),
        "runs": count("feed_sync_runs"),
        "clicks": count("click_events") if cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='click_events'").fetchone() else 0,
    }
finally:
    con.close()

print(f"Backup created: {backup}")
print(f"Deals      : {before['deals']} -> {after['deals']} (deleted {deleted_deals})")
print(f"Providers  : {before['providers']} -> {after['providers']} (deleted {deleted_providers})")
print(f"Sync runs  : {before['runs']} -> {after['runs']} (deleted {deleted_runs})")
print(f"Click events: {before['clicks']} -> {after['clicks']} (deleted {deleted_clicks})")
'@

  Set-Content -Path $tmpScript -Value $pythonCode -Encoding UTF8
  try {
    python $tmpScript $dbPath $clearClicksArg
  } finally {
    if (Test-Path $tmpScript) { Remove-Item $tmpScript -Force }
  }
}

Write-Host ""
if ($Apply) {
  Write-Host "Stage 59 cleanup finished." -ForegroundColor Green
} else {
  Write-Host "Dry run finished. Re-run with -Apply when ready." -ForegroundColor Yellow
}
