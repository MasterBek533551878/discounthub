param(
  [string]$BaseUrl = "http://127.0.0.1:8000",
  [string]$AdminToken = "dev-local-admin-token"
)

Invoke-RestMethod `
  -Method Get `
  -Uri "$BaseUrl/admin/feed-providers/scheduler/status" `
  -Headers @{ "X-Admin-Token" = $AdminToken }
