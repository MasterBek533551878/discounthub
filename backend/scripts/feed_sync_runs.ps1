param(
  [string]$BaseUrl = "http://127.0.0.1:8000",
  [string]$AdminToken = "dev-local-admin-token",
  [int]$Limit = 20,
  [string]$ProviderId = "",
  [string]$Status = ""
)

$query = "limit=$Limit"
if ($ProviderId -ne "") { $query += "&provider_id=$([uri]::EscapeDataString($ProviderId))" }
if ($Status -ne "") { $query += "&status=$([uri]::EscapeDataString($Status))" }

Invoke-RestMethod `
  -Uri "$BaseUrl/admin/feed-providers/sync-runs?$query" `
  -Headers @{ "X-Admin-Token" = $AdminToken }
