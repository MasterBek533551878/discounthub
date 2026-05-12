param(
  [string]$BaseUrl = "http://127.0.0.1:8000",
  [string]$AdminToken = "dev-local-admin-token",
  [Parameter(Mandatory = $true)]
  [string]$FeedUrl,
  [switch]$Replace
)

$body = @{
  url = $FeedUrl
  replace = [bool]$Replace
  timeoutSeconds = 20
} | ConvertTo-Json -Depth 10

$response = Invoke-RestMethod `
  -Method Post `
  -Uri "$BaseUrl/admin/deals/import-url" `
  -Headers @{ "X-Admin-Token" = $AdminToken } `
  -ContentType "application/json" `
  -Body $body

$response
