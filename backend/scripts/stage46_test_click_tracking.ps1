$ErrorActionPreference = "Stop"

$BaseUrl = "http://127.0.0.1:8000"

Write-Host "Checking backend health..." -ForegroundColor Cyan
Invoke-RestMethod "$BaseUrl/health" | Format-List

Write-Host "Fetching first deal..." -ForegroundColor Cyan
$page = Invoke-RestMethod "$BaseUrl/deals?sort=discount_desc&page=1&page_size=1&currency=USD"
if (-not $page.items -or $page.items.Count -eq 0) {
  throw "No deals returned from API. Sync providers first."
}

$deal = $page.items[0]
Write-Host "Testing click for:" $deal.title -ForegroundColor Cyan
Write-Host "Deal ID:" $deal.id

$encodedId = [System.Uri]::EscapeDataString($deal.id)
$clickUrl = "$BaseUrl/deals/$encodedId/click"
Write-Host "Click URL:" $clickUrl

try {
  Invoke-WebRequest -Uri $clickUrl -MaximumRedirection 0 -ErrorAction Stop | Out-Null
} catch {
  $response = $_.Exception.Response
  if ($response -and [int]$response.StatusCode -in 301,302,303,307,308) {
    Write-Host "Redirect OK:" $response.Headers.Location -ForegroundColor Green
  } else {
    throw
  }
}

Write-Host "Click summary:" -ForegroundColor Cyan
Invoke-RestMethod "$BaseUrl/clicks/summary?limit=10" | ConvertTo-Json -Depth 8
