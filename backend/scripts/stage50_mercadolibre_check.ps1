param(
  [string]$BaseUrl = 'http://127.0.0.1:8000',
  [string]$AdminToken = 'dev-local-admin-token'
)

$ErrorActionPreference = 'Stop'
$headers = @{ 'X-Admin-Token' = $AdminToken }

Write-Host 'Health' -ForegroundColor Cyan
Invoke-RestMethod -Uri "$BaseUrl/health" -Method Get

Write-Host 'Storage' -ForegroundColor Cyan
Invoke-RestMethod -Uri "$BaseUrl/storage/status" -Method Get

Write-Host 'Mercado Libre providers' -ForegroundColor Cyan
Invoke-RestMethod -Uri "$BaseUrl/admin/feed-providers" -Method Get -Headers $headers |
  Select-Object -ExpandProperty items |
  Where-Object { $_.adapter -eq 'mercadolibre_search_api' -or $_.name -like '*Mercado*' } |
  Select-Object name, enabled, lastStatus, lastImportedCount

Write-Host 'Mercado Libre marketplaces' -ForegroundColor Cyan
Invoke-RestMethod -Uri "$BaseUrl/marketplaces" -Method Get

Write-Host 'Mercado Libre deals sample' -ForegroundColor Cyan
Invoke-RestMethod -Uri "$BaseUrl/deals?q=Mercado&page_size=10&sort=newest" -Method Get
