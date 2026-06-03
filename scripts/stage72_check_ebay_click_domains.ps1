param(
  [string]$ApiBaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"
Write-Host "== DiscountHub Stage 72: eBay click domain check =="
Write-Host "API: $ApiBaseUrl"
Write-Host ""

$health = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/health" -TimeoutSec 10
Write-Host "Backend health: $($health.status) ($($health.service))"
Write-Host ""

function Get-RedirectLocation([string]$Url) {
  $request = [System.Net.HttpWebRequest]::Create($Url)
  $request.Method = "GET"
  $request.AllowAutoRedirect = $false
  $request.Timeout = 15000
  $response = $request.GetResponse()
  try {
    return $response.Headers["Location"]
  } finally {
    $response.Close()
  }
}

$platforms = @("eBay US", "eBay MOTORS_US", "eBay ES", "eBay GB", "eBay DE", "eBay IT", "eBay AU", "eBay FR")
foreach ($platform in $platforms) {
  $encoded = [System.Uri]::EscapeDataString($platform)
  $page = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals?platform=$encoded&page_size=1&sort=newest" -TimeoutSec 20
  if (-not $page.items -or $page.items.Count -eq 0) {
    Write-Host "Platform : $platform"
    Write-Host "Status   : no sample deals"
    Write-Host ""
    continue
  }

  $deal = $page.items[0]
  $dealId = [System.Uri]::EscapeDataString($deal.id)
  $click = "$ApiBaseUrl/deals/$dealId/click"
  $location = Get-RedirectLocation $click

  Write-Host "Platform : $platform"
  Write-Host "Deal ID  : $($deal.id)"
  Write-Host "Product  : $($deal.productUrl)"
  Write-Host "Location : $location"
  Write-Host ""
}

Write-Host "Stage 72 check completed."
