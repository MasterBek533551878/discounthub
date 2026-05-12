param(
  [string]$DatabasePath = "data/discounthub.sqlite3",
  [switch]$NoBackup,
  [int]$TrimSyncRuns = 0
)

$ErrorActionPreference = "Stop"
$BackendRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $BackendRoot

$Python = "python"
$ArgsList = @(".\scripts\stage48_mvp_cleanup.py", "--db", $DatabasePath)
if ($NoBackup) { $ArgsList += "--no-backup" }
if ($TrimSyncRuns -gt 0) { $ArgsList += @("--trim-sync-runs", "$TrimSyncRuns") }

& $Python @ArgsList
