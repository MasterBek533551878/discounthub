param(
  [string]$ApiBase = "http://127.0.0.1:8000",
  [string]$AdminToken = "dev-local-admin-token"
)

$headers = @{ "X-Admin-Token" = $AdminToken }

Invoke-RestMethod `
  -Method Post `
  -Uri "$ApiBase/admin/feed-providers/sync-all" `
  -Headers $headers
