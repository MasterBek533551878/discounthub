param(
  [string]$BaseUrl = "http://127.0.0.1:8000",
  [string]$AdminToken = "dev-local-admin-token"
)

Invoke-RestMethod `
  -Method Delete `
  -Uri "$BaseUrl/admin/feed-providers/sync-runs" `
  -Headers @{ "X-Admin-Token" = $AdminToken }
