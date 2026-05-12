Param(
    [string]$BackendBaseUrl = "http://127.0.0.1:8000",
    [string]$FeedBaseUrl = "http://127.0.0.1:9000",
    [string]$AdminToken = "dev-local-admin-token"
)

$ErrorActionPreference = "Continue"

function Test-JsonEndpoint {
    param(
        [string]$Name,
        [string]$Url,
        [hashtable]$Headers = @{}
    )

    try {
        $response = Invoke-RestMethod -Uri $Url -Headers $Headers -TimeoutSec 8
        Write-Host "[OK] $Name -> $Url" -ForegroundColor Green
        return $response
    } catch {
        Write-Host "[FAIL] $Name -> $Url" -ForegroundColor Red
        Write-Host "       $($_.Exception.Message)" -ForegroundColor DarkYellow
        return $null
    }
}

Write-Host "DiscountHub dev health check" -ForegroundColor Cyan
Write-Host "Backend: $BackendBaseUrl"
Write-Host "Feed:    $FeedBaseUrl"
Write-Host ""

$health = Test-JsonEndpoint -Name "Backend health" -Url "$BackendBaseUrl/health"
$storage = Test-JsonEndpoint -Name "Storage status" -Url "$BackendBaseUrl/storage/status"
$deals = Test-JsonEndpoint -Name "Deals API" -Url "$BackendBaseUrl/deals?page_size=5"
$feed = Test-JsonEndpoint -Name "Demo feed" -Url "$FeedBaseUrl/provider_feed.json"
$genericFeed = Test-JsonEndpoint -Name "Generic adapter feed" -Url "$FeedBaseUrl/provider_feed_generic.json"
$googleFeed = Test-JsonEndpoint -Name "Google Merchant adapter feed" -Url "$FeedBaseUrl/provider_feed_google_merchant.json"
$awinFeed = Test-JsonEndpoint -Name "Awin adapter feed" -Url "$FeedBaseUrl/provider_feed_awin.json"
$providers = Test-JsonEndpoint -Name "Feed providers" -Url "$BackendBaseUrl/admin/feed-providers" -Headers @{ "X-Admin-Token" = $AdminToken }
$scheduler = Test-JsonEndpoint -Name "Feed scheduler status" -Url "$BackendBaseUrl/admin/feed-providers/scheduler/status" -Headers @{ "X-Admin-Token" = $AdminToken }

Write-Host ""
Write-Host "Summary" -ForegroundColor Cyan
if ($storage) {
    Write-Host "Deals in storage: $($storage.dealCount)"
}
if ($providers) {
    Write-Host "Feed providers:   $($providers.total)"
}
if ($scheduler) {
    Write-Host "Scheduler status: enabled=$($scheduler.enabled), lastStatus=$($scheduler.lastStatus)"
}

if ($health -and $storage -and $deals -and $feed) {
    Write-Host "Core local dev environment is OK." -ForegroundColor Green
} else {
    Write-Host "Some services are not reachable. Make sure backend :8000 and feed server :9000 are running." -ForegroundColor Yellow
}
