$ErrorActionPreference = "Stop"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  Write-Host "Docker is not installed or not available in PATH." -ForegroundColor Yellow
  Write-Host "Install Docker Desktop, restart PowerShell, then run this script again." -ForegroundColor Yellow
  Write-Host "For non-Docker local testing, run:" -ForegroundColor Cyan
  Write-Host "  .\scripts\production_start_local.ps1" -ForegroundColor Cyan
  exit 1
}

docker build -t discounthub-api:local .
