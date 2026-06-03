param(
  [string]$BaseUrl = 'http://127.0.0.1:8000',
  [string]$AdminToken = 'dev-local-admin-token',
  [string]$ProviderId = 'awin_feed_list',
  [int]$MaxFeeds = 20,
  [int]$MaxItemsPerFeed = 80,
  [int]$MinDiscountPercent = 10,
  [int]$TimeoutSeconds = 60,
  [int]$WaitSeconds = 20
)

$ErrorActionPreference = 'Stop'

function Wait-BackendReady {
  param(
    [Parameter(Mandatory = $true)][string]$Url,
    [int]$Seconds = 20
  )

  $deadline = (Get-Date).AddSeconds($Seconds)
  do {
    try {
      Invoke-RestMethod -Uri "$Url/health" -Method Get -TimeoutSec 3 | Out-Null
      return
    } catch {
      Start-Sleep -Seconds 1
    }
  } while ((Get-Date) -lt $deadline)

  throw "Backend is not reachable at $Url. Start backend first."
}

Wait-BackendReady -Url $BaseUrl -Seconds $WaitSeconds

$providerUrl = "awin://feed-list?max_feeds=$MaxFeeds&max_items_per_feed=$MaxItemsPerFeed&min_discount_percent=$MinDiscountPercent&joined_only=true"
$body = @{
  id = $ProviderId
  name = 'Awin Product Feed List - joined advertisers'
  url = $providerUrl
  adapter = 'awin_feed_list_api'
  enabled = $true
  replaceOnSync = $false
  monetizationMode = 'affiliate'
} | ConvertTo-Json -Depth 10

$headers = @{ 'X-Admin-Token' = $AdminToken }

Write-Host "Registering Awin provider: $ProviderId" -ForegroundColor Cyan
Invoke-RestMethod -Uri "$BaseUrl/admin/feed-providers" -Method Post -Headers $headers -ContentType 'application/json' -Body $body | Out-Null

Write-Host "Syncing Awin provider: $ProviderId" -ForegroundColor Cyan
Invoke-RestMethod -Uri "$BaseUrl/admin/feed-providers/$ProviderId/sync?timeout_seconds=$TimeoutSeconds" -Method Post -Headers $headers
