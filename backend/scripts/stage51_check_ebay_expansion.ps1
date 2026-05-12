param(
  [string]$BaseUrl = 'http://127.0.0.1:8000',
  [string]$AdminToken = 'dev-local-admin-token'
)

$ErrorActionPreference = 'Stop'
$headers = @{ 'X-Admin-Token' = $AdminToken }

Write-Host 'Health' -ForegroundColor Cyan
Invoke-RestMethod "$BaseUrl/health"

Write-Host ''
Write-Host 'Storage' -ForegroundColor Cyan
Invoke-RestMethod "$BaseUrl/storage/status"

Write-Host ''
Write-Host 'Categories' -ForegroundColor Cyan
Invoke-RestMethod "$BaseUrl/categories"

Write-Host ''
Write-Host 'Marketplaces' -ForegroundColor Cyan
Invoke-RestMethod "$BaseUrl/marketplaces"

Write-Host ''
Write-Host 'Stage 51 providers' -ForegroundColor Cyan
Invoke-RestMethod "$BaseUrl/admin/feed-providers" -Headers $headers |
  Select-Object -ExpandProperty items |
  Where-Object { ([string]$_.id).StartsWith('ebay_expansion_') } |
  Select-Object id, name, enabled, lastStatus, lastImportedCount |
  Format-Table -AutoSize

Write-Host ''
Write-Host 'Sample Stage 51 deals' -ForegroundColor Cyan
Invoke-RestMethod "$BaseUrl/deals?q=eBay%20Expansion&page_size=5&sort=newest"
