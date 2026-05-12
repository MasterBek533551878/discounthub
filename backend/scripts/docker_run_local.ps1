$ErrorActionPreference = "Stop"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  Write-Host "Docker is not installed or not available in PATH." -ForegroundColor Yellow
  Write-Host "Install Docker Desktop, restart PowerShell, then run this script again." -ForegroundColor Yellow
  Write-Host "For non-Docker local testing, run:" -ForegroundColor Cyan
  Write-Host "  .\scripts\production_start_local.ps1" -ForegroundColor Cyan
  exit 1
}

$containerName = "discounthub-api-local"
$existing = docker ps -a --filter "name=$containerName" --format "{{.Names}}"

if ($existing -eq $containerName) {
  docker rm -f $containerName | Out-Null
}

docker run --name $containerName `
  -p 8000:8000 `
  -e ENVIRONMENT=production `
  -e ADMIN_TOKEN=dev-local-admin-token `
  -e FEED_SCHEDULER_ENABLED=true `
  -e FEED_SCHEDULER_RUN_ON_STARTUP=true `
  discounthub-api:local
