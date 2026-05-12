param(
  [string]$BaseUrl = 'http://127.0.0.1:8000',
  [string]$AdminToken = 'dev-local-admin-token',
  [string[]]$Platforms = @('eBay US', 'eBay UK', 'eBay DE', 'eBay FR', 'eBay IT', 'eBay ES', 'eBay AU', 'eBay Germany', 'eBay France', 'eBay Italy', 'eBay Spain', 'eBay Australia', 'eBay'),
  [switch]$DeleteAllPlatformDeals
)

$ErrorActionPreference = 'Stop'

Write-Host 'DiscountHub eBay deals cleanup' -ForegroundColor Cyan
Write-Host "Backend: $BaseUrl"
Write-Host "Mode:    delete imported eBay ids only"
if ($DeleteAllPlatformDeals) {
  Write-Host 'Mode override: delete all deals from eBay platforms' -ForegroundColor Yellow
}

try {
  Invoke-RestMethod -Uri "$BaseUrl/health" -Method Get -TimeoutSec 5 | Out-Null
} catch {
  throw "Backend is not reachable at $BaseUrl. Start run_all_dev.ps1 first."
}

$headers = @{ 'X-Admin-Token' = $AdminToken }
$totalDeleted = 0
$totalSkipped = 0

foreach ($platform in $Platforms) {
  Write-Host "Scanning platform: $platform" -ForegroundColor Yellow
  do {
    $encodedPlatform = [System.Uri]::EscapeDataString($platform)
    $response = Invoke-RestMethod -Uri "$BaseUrl/admin/deals?platform=$encodedPlatform&page_size=100&sort=newest" -Method Get -Headers $headers -TimeoutSec 30
    $items = @($response.items)
    $deletedThisPage = 0

    foreach ($deal in $items) {
      $dealId = [string]$deal.id
      if (-not $DeleteAllPlatformDeals -and -not $dealId.StartsWith('ebay_')) {
        $totalSkipped++
        Write-Host "Skipped non-imported eBay-like deal: $dealId" -ForegroundColor DarkGray
        continue
      }

      $encodedId = [System.Uri]::EscapeDataString($dealId)
      Invoke-RestMethod -Uri "$BaseUrl/admin/deals/$encodedId" -Method Delete -Headers $headers -TimeoutSec 30 | Out-Null
      $totalDeleted++
      $deletedThisPage++
      Write-Host "Deleted: $dealId"
    }

    # If a page only had skipped non-imported items, continuing would loop forever.
    if ($deletedThisPage -eq 0) { break }
  } while ($items.Count -gt 0)
}

Write-Host "Deleted eBay imported deal(s): $totalDeleted" -ForegroundColor Green
if ($totalSkipped -gt 0) {
  Write-Host "Skipped non-imported eBay-like deal(s): $totalSkipped" -ForegroundColor Yellow
}
