param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$AdminToken = "dev-local-admin-token",
    [string]$FeedUrl = "http://127.0.0.1:9000/provider_feed_awin.json"
)

$body = @{
    id = "awin_demo"
    name = "Awin-like products feed"
    url = $FeedUrl
    adapter = "awin_products"
    enabled = $true
    replaceOnSync = $false
} | ConvertTo-Json -Depth 8

Invoke-RestMethod `
    -Method Post `
    -Uri "$BaseUrl/admin/feed-providers" `
    -Headers @{ "X-Admin-Token" = $AdminToken } `
    -ContentType "application/json" `
    -Body $body
