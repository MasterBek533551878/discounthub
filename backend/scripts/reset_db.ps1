# Deletes the local SQLite database. It will be recreated and seeded on the next backend start.
$ErrorActionPreference = "Stop"

$backendRoot = Split-Path -Parent $PSScriptRoot
$dbPath = Join-Path $backendRoot "data\discounthub.sqlite3"

if (Test-Path $dbPath) {
  Remove-Item $dbPath -Force
  Write-Host "Removed $dbPath"
} else {
  Write-Host "Database file does not exist: $dbPath"
}
