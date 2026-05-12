param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$AdminToken = "dev-local-admin-token",
    [string]$ProviderId = "affiliate_csv_global",
    [string]$Name = "Affiliate CSV global feed",
    [string]$FeedUrl = "http://127.0.0.1:9000/provider_feed_affiliate.csv",
    [ValidateSet("csv_products", "generic_products", "awin_products", "admitad_products", "rakuten_products", "cj_products", "impact_products")]
    [string]$Adapter = "csv_products",
    [switch]$ReplaceOnSync
)

$body = @{
    id = $ProviderId
    name = $Name
    url = $FeedUrl
    adapter = $Adapter
    enabled = $true
    replaceOnSync = [bool]$ReplaceOnSync
} | ConvertTo-Json -Depth 8

Write-Host "Registering affiliate feed provider..." -ForegroundColor Cyan
Write-Host "Provider: $ProviderId" -ForegroundColor DarkGray
Write-Host "Adapter:  $Adapter" -ForegroundColor DarkGray
Write-Host "Feed URL: $FeedUrl" -ForegroundColor DarkGray

Invoke-RestMethod `
    -Method Post `
    -Uri "$BaseUrl/admin/feed-providers" `
    -Headers @{ "X-Admin-Token" = $AdminToken } `
    -ContentType "application/json" `
    -Body $body
