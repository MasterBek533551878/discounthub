param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$AdminToken = "dev-local-admin-token",
    [string]$ProviderId = "affiliate_csv_global"
)

Write-Host "Syncing affiliate feed provider: $ProviderId" -ForegroundColor Cyan
Invoke-RestMethod `
    -Method Post `
    -Uri "$BaseUrl/admin/feed-providers/$ProviderId/sync" `
    -Headers @{ "X-Admin-Token" = $AdminToken } | ConvertTo-Json -Depth 8

Write-Host "\nFirst imported deals:" -ForegroundColor Cyan
Invoke-RestMethod "$BaseUrl/deals?page_size=5&sort=newest" | ConvertTo-Json -Depth 8
