param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$AdminToken = "dev-local-admin-token"
)

$providerIds = @("generic_feed", "google_merchant_demo", "awin_demo")
foreach ($providerId in $providerIds) {
    Write-Host "Syncing $providerId..."
    Invoke-RestMethod `
        -Method Post `
        -Uri "$BaseUrl/admin/feed-providers/$providerId/sync" `
        -Headers @{ "X-Admin-Token" = $AdminToken }
}
