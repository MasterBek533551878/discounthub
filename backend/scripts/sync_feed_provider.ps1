param(
  [string]$ApiBase = "http://127.0.0.1:8000",
  [string]$AdminToken = "dev-local-admin-token",
  [string]$ProviderId = "demo_feed"
)

$headers = @{ "X-Admin-Token" = $AdminToken }

Invoke-RestMethod `
  -Method Post `
  -Uri "$ApiBase/admin/feed-providers/$ProviderId/sync" `
  -Headers $headers
