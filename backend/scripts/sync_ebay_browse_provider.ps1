param(
  [string]$ProviderId = 'ebay_browse_headphones',
  [string]$BaseUrl = 'http://127.0.0.1:8000',
  [string]$AdminToken = 'dev-local-admin-token'
)

$ErrorActionPreference = 'Stop'

Invoke-RestMethod `
  -Uri "$BaseUrl/admin/feed-providers/$ProviderId/sync" `
  -Method Post `
  -Headers @{ 'X-Admin-Token' = $AdminToken }
