param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$AdminToken = "dev-local-admin-token",
    [string]$FeedUrl = "http://127.0.0.1:9000/provider_feed_affiliate.csv"
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
& (Join-Path $scriptDir "stage47_add_affiliate_feed_provider.ps1") `
    -BaseUrl $BaseUrl `
    -AdminToken $AdminToken `
    -ProviderId "affiliate_csv_global" `
    -Name "Affiliate CSV global feed" `
    -FeedUrl $FeedUrl `
    -Adapter "csv_products"

& (Join-Path $scriptDir "stage47_sync_affiliate_feed_provider.ps1") `
    -BaseUrl $BaseUrl `
    -AdminToken $AdminToken `
    -ProviderId "affiliate_csv_global"
