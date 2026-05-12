param(
  [string]$ApiBase = "http://127.0.0.1:8000",
  [string]$AdminToken = "dev-local-admin-token",
  [string]$ProviderId = "demo_feed",
  [string]$Name = "Demo provider feed",
  [string]$Url = "http://127.0.0.1:9000/provider_feed.json",
  [switch]$Disabled,
  [switch]$ReplaceOnSync
)

$headers = @{ "X-Admin-Token" = $AdminToken }
$payload = @{
  id = $ProviderId
  name = $Name
  url = $Url
  enabled = -not $Disabled.IsPresent
  replaceOnSync = $ReplaceOnSync.IsPresent
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Method Post `
  -Uri "$ApiBase/admin/feed-providers" `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $payload
