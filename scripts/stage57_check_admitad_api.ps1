param(
  [string]$EnvPath = "backend/.env",
  [string]$Scope = "advcampaigns advcampaigns_for_website websites",
  [int]$Limit = 20
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot/stage57_common_admitad.ps1"

Write-Host "== DiscountHub Stage 57 Admitad API check =="
Write-Host "Env: $EnvPath"
Write-Host ""

$settings = Get-AdmitadSettings -EnvPath $EnvPath
Write-Host "Website/ad space ID: $($settings.WebsiteId)"
Write-Host "API: $($settings.ApiBaseUrl)"
Write-Host "Client ID: configured"
Write-Host "Client secret: configured"
Write-Host ""

Write-Host "[1/4] OAuth client credentials"
$token = Get-AdmitadAccessToken -Settings $settings -Scope $Scope
Write-Host "Token: OK (not printed)"
Write-Host "Expires in: $($token.expires_in) seconds"
Write-Host ""

Write-Host "[2/4] Pending programs"
$pending = Invoke-AdmitadGet -Settings $settings -AccessToken $token.access_token -PathAndQuery "/advcampaigns/website/$($settings.WebsiteId)/?limit=$Limit&connection_status=pending"
$pendingItems = @(Get-AdmitadResultsArray $pending)
$pendingItems | Select-Object -First 10 @{Name="id";Expression={$_.id}}, @{Name="name";Expression={$_.name}}, @{Name="connectionStatus";Expression={$_.connection_status}}, @{Name="productFeeds";Expression={$_.show_products_links}} | ConvertTo-Json -Depth 5
Write-Host "Pending count returned: $($pendingItems.Count)"
Write-Host ""

Write-Host "[3/4] Active programs"
$active = Invoke-AdmitadGet -Settings $settings -AccessToken $token.access_token -PathAndQuery "/advcampaigns/website/$($settings.WebsiteId)/?limit=$Limit&connection_status=active"
$activeItems = @(Get-AdmitadResultsArray $active)
$activeItems | Select-Object -First 10 @{Name="id";Expression={$_.id}}, @{Name="name";Expression={$_.name}}, @{Name="connectionStatus";Expression={$_.connection_status}}, @{Name="productFeeds";Expression={$_.show_products_links}} | ConvertTo-Json -Depth 5
Write-Host "Active count returned: $($activeItems.Count)"
Write-Host ""

Write-Host "[4/4] Active programs with product feeds"
$feedPrograms = @($activeItems | Where-Object { $_.show_products_links -eq $true -or $_.products_csv_link -or $_.products_xml_link -or $_.feeds_info })
$feedPrograms | Select-Object -First 10 @{Name="id";Expression={$_.id}}, @{Name="name";Expression={$_.name}}, @{Name="hasCsv";Expression={[bool]$_.products_csv_link}}, @{Name="feedsInfo";Expression={@($_.feeds_info).Count}} | ConvertTo-Json -Depth 5
Write-Host "Active feed-capable programs returned: $($feedPrograms.Count)"
Write-Host ""

if ($activeItems.Count -eq 0) {
  Write-Warning "No active Admitad programs yet. This is normal while AliExpress/iHerb/Geekbuying/etc. are under moderation. Wait for approval, then run this script again."
} elseif ($feedPrograms.Count -eq 0) {
  Write-Warning "Some programs are active, but no CSV product feeds were returned yet. Open Product Feeds in Admitad or wait for feed access."
} else {
  Write-Host "Admitad API is ready. Next: run scripts/stage57_register_active_admitad_product_feeds.ps1"
}

Write-Host "Stage 57 Admitad API check completed."
