param(
  [string]$ApiBaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

function Get-Json($Url) {
  Invoke-RestMethod -Method Get -Uri $Url -TimeoutSec 30
}

function Get-FirstRedirectLocation($Url) {
  Add-Type -AssemblyName System.Net.Http | Out-Null
  $handler = [System.Net.Http.HttpClientHandler]::new()
  $handler.AllowAutoRedirect = $false
  $client = [System.Net.Http.HttpClient]::new($handler)
  try {
    $request = [System.Net.Http.HttpRequestMessage]::new([System.Net.Http.HttpMethod]::Get, $Url)
    $response = $client.SendAsync($request).GetAwaiter().GetResult()
    $location = $response.Headers.Location
    if ($null -eq $location) { return "" }
    return [string]$location
  } finally {
    $client.Dispose()
    $handler.Dispose()
  }
}

Write-Host "== DiscountHub Stage 68: partner click target check =="
Write-Host "API: $ApiBaseUrl"
Write-Host ""

$health = Get-Json "$ApiBaseUrl/health"
Write-Host "Backend health: $($health.status) ($($health.service))"
Write-Host ""

$platforms = @("AliExpress WW", "AliExpress PL", "eBay US", "eBay GB")
foreach ($platform in $platforms) {
  $encoded = [uri]::EscapeDataString($platform)
  $page = Get-Json "$ApiBaseUrl/deals?platform=$encoded&page_size=1&sort=newest"
  if (-not $page.items -or $page.items.Count -eq 0) {
    Write-Warning "No sample deal found for platform: $platform"
    continue
  }

  $deal = $page.items[0]
  $clickUrl = "$ApiBaseUrl/deals/$([uri]::EscapeDataString($deal.id))/click"
  $location = Get-FirstRedirectLocation $clickUrl

  Write-Host "Platform : $platform"
  Write-Host "Deal ID  : $($deal.id)"
  Write-Host "Title    : $($deal.title)"
  Write-Host "Product  : $($deal.productUrl)"
  Write-Host "Affiliate: $($deal.affiliateUrl)"
  Write-Host "Click    : $clickUrl"
  Write-Host "Location : $location"

  if ($platform -eq "AliExpress WW") {
    if ($location -notmatch "ad\.admitad\.com/g/" -or $location -notmatch "ulp=.*aliexpress.*item") {
      Write-Warning "AliExpress WW click does not look like a canonical Admitad product deeplink."
    }
  }
  if ($platform -match "eBay") {
    if ($location -match "_skw=|hash=|amdata=") {
      Write-Warning "eBay click still contains noisy search/hash parameters."
    }
  }

  Write-Host ""
}

Write-Host "Stage 68 click target check completed."
