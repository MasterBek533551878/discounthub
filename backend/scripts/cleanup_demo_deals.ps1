param(
  [string]$BaseUrl = 'http://127.0.0.1:8000',
  [string]$AdminToken = 'dev-local-admin-token',
  [switch]$DeleteKnownDemoPlatforms
)

$ErrorActionPreference = 'Stop'

$KnownDemoIds = @(
  'deal_001',
  'deal_002',
  'deal_003',
  'deal_004',
  'deal_005',
  'deal_006',
  'deal_007',
  'deal_008',
  'deal_custom_001',
  'deal_import_001',
  'feed_demo_001',
  'generic_001',
  'gm_001',
  'awin_001',
  'provider_product_001'
)

$KnownDemoPlatforms = @(
  'DemoShop',
  'FeedShop',
  'GenericShop',
  'HomeLite',
  'AwinDemoStore',
  'Amazon',
  'AliExpress',
  'Alibaba'
)

function Invoke-DeleteDeal {
  param(
    [Parameter(Mandatory = $true)][string]$DealId,
    [Parameter(Mandatory = $true)]$Headers
  )

  if ([string]::IsNullOrWhiteSpace($DealId)) {
    return $false
  }

  $encodedId = [System.Uri]::EscapeDataString($DealId)
  try {
    Invoke-RestMethod -Uri "$BaseUrl/admin/deals/$encodedId" -Method Delete -Headers $Headers -TimeoutSec 30 | Out-Null
    Write-Host "Deleted: $DealId"
    return $true
  } catch {
    $response = $_.Exception.Response
    if ($null -ne $response -and [int]$response.StatusCode -eq 404) {
      Write-Host "Already absent: $DealId" -ForegroundColor DarkGray
      return $false
    }
    throw
  }
}

Write-Host 'DiscountHub demo deals cleanup' -ForegroundColor Cyan
Write-Host "Backend: $BaseUrl"
Write-Host 'Mode:    delete known demo ids'
if ($DeleteKnownDemoPlatforms) {
  Write-Host 'Mode override: also delete all deals from known demo platforms' -ForegroundColor Yellow
}

try {
  Invoke-RestMethod -Uri "$BaseUrl/health" -Method Get -TimeoutSec 5 | Out-Null
} catch {
  throw "Backend is not reachable at $BaseUrl. Start run_all_dev.ps1 first."
}

$headers = @{ 'X-Admin-Token' = $AdminToken }
$totalDeleted = 0

foreach ($dealId in $KnownDemoIds) {
  if (Invoke-DeleteDeal -DealId $dealId -Headers $headers) {
    $totalDeleted++
  }
}

if ($DeleteKnownDemoPlatforms) {
  foreach ($platform in $KnownDemoPlatforms) {
    Write-Host "Scanning platform: $platform" -ForegroundColor Yellow
    do {
      $encodedPlatform = [System.Uri]::EscapeDataString($platform)
      $response = Invoke-RestMethod -Uri "$BaseUrl/admin/deals?platform=$encodedPlatform&page_size=100&sort=newest" -Method Get -Headers $headers -TimeoutSec 30
      $items = @($response.items)
      $deletedThisPage = 0

      foreach ($deal in $items) {
        $dealId = [string]$deal.id
        if ($dealId.StartsWith('ebay_')) {
          Write-Host "Skipped imported eBay deal on demo-like platform: $dealId" -ForegroundColor DarkGray
          continue
        }

        if (Invoke-DeleteDeal -DealId $dealId -Headers $headers) {
          $totalDeleted++
          $deletedThisPage++
        }
      }

      if ($deletedThisPage -eq 0) { break }
    } while ($items.Count -gt 0)
  }
}

Write-Host "Deleted demo deal(s): $totalDeleted" -ForegroundColor Green
