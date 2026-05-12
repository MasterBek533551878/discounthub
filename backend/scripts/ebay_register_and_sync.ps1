param(
  [string]$ProviderId = 'ebay_browse_headphones',
  [string]$BaseUrl = 'http://127.0.0.1:8000',
  [string]$AdminToken = 'dev-local-admin-token'
)

$ErrorActionPreference = 'Stop'

Write-Host 'Registering providers from config...' -ForegroundColor Cyan
& "$PSScriptRoot\provider_sync_from_config.ps1" -BaseUrl $BaseUrl -AdminToken $AdminToken

Write-Host ''
Write-Host "Syncing eBay provider: $ProviderId" -ForegroundColor Cyan
& "$PSScriptRoot\sync_ebay_browse_provider.ps1" -ProviderId $ProviderId -BaseUrl $BaseUrl -AdminToken $AdminToken
