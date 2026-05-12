Param(
    [string]$AdminToken = "dev-local-admin-token"
)

$ErrorActionPreference = "Stop"
$BackendRoot = Split-Path -Parent $PSScriptRoot
Set-Location $BackendRoot

Write-Host "Adding demo adapter feed providers..." -ForegroundColor Cyan
& "$PSScriptRoot\add_generic_feed_provider.ps1" -AdminToken $AdminToken | Out-Null
& "$PSScriptRoot\add_google_merchant_feed_provider.ps1" -AdminToken $AdminToken | Out-Null
& "$PSScriptRoot\add_awin_feed_provider.ps1" -AdminToken $AdminToken | Out-Null

Write-Host "Running sync for all demo adapter providers..." -ForegroundColor Cyan
& "$PSScriptRoot\sync_adapter_demo_providers.ps1" -AdminToken $AdminToken

Write-Host "Storage status:" -ForegroundColor Cyan
Invoke-RestMethod -Uri "http://127.0.0.1:8000/storage/status"
