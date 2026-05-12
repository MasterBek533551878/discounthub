param(
  [string]$BaseUrl = "http://127.0.0.1:8000",
  [string]$AdminToken = "dev-local-admin-token"
)

$ErrorActionPreference = "Stop"

function Test-Endpoint($Name, $Url, $Headers = @{}) {
  try {
    $result = Invoke-RestMethod -Uri $Url -Headers $Headers -TimeoutSec 20
    Write-Host "[OK] $Name -> $Url" -ForegroundColor Green
    return $result
  } catch {
    Write-Host "[FAIL] $Name -> $Url" -ForegroundColor Red
    Write-Host "       $($_.Exception.Message)" -ForegroundColor Yellow
    return $null
  }
}

Write-Host "DiscountHub production health check" -ForegroundColor Cyan
Write-Host "Base URL: $BaseUrl"
Write-Host ""

$health = Test-Endpoint "Health" "$BaseUrl/health"
$security = Test-Endpoint "Security" "$BaseUrl/security/status"
$storage = Test-Endpoint "Storage" "$BaseUrl/storage/status"
$deals = Test-Endpoint "Deals" "$BaseUrl/deals?page_size=5"
$scheduler = Test-Endpoint "Scheduler" "$BaseUrl/admin/feed-providers/scheduler/status" @{ "X-Admin-Token" = $AdminToken }

Write-Host ""
if ($health -and $storage -and $deals) {
  Write-Host "Core production API is reachable." -ForegroundColor Green
} else {
  Write-Host "Production API check failed. Review logs and env vars." -ForegroundColor Red
}

if ($security) {
  Write-Host "Environment: $($security.environment), security status: $($security.status)"
}
if ($storage) {
  Write-Host "Deals in storage: $($storage.dealCount)"
}
if ($scheduler) {
  Write-Host "Scheduler enabled: $($scheduler.enabled), lastStatus: $($scheduler.lastStatus)"
}
