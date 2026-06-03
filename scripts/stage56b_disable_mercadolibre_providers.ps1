param(
  [string]$ApiBaseUrl = "http://127.0.0.1:8000",
  [string]$AdminToken = "dev-local-admin-token"
)

$ErrorActionPreference = "Stop"

Write-Host "== DiscountHub Stage 56b disable Mercado Libre direct providers =="
Write-Host "API: $ApiBaseUrl"
Write-Host ""

$headers = @{ "X-Admin-Token" = $AdminToken }

Write-Host "[1/3] Health"
$health = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/health"
Write-Host "Health: $($health.status) ($($health.service))"
Write-Host ""

Write-Host "[2/3] Loading providers"
$providersResponse = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/admin/feed-providers" -Headers $headers
$providers = @($providersResponse.items | Where-Object { $_.id -like "mercadolibre_*_direct_v1" })
Write-Host "Mercado Libre Stage 56 providers found: $($providers.Count)"

$updated = 0
foreach ($provider in $providers) {
  $bodyObject = [ordered]@{
    id = $provider.id
    name = $provider.name
    url = $provider.url
    adapter = $provider.adapter
    enabled = $false
    replaceOnSync = $provider.replaceOnSync
    monetizationMode = $provider.monetizationMode
  }
  $body = $bodyObject | ConvertTo-Json -Depth 8
  $result = Invoke-RestMethod -Method Post -Uri "$ApiBaseUrl/admin/feed-providers" -Headers $headers -ContentType "application/json" -Body $body
  $updated += 1
  Write-Host ("Disabled: {0}; enabled={1}; lastStatus={2}" -f $result.id, $result.enabled, $result.lastStatus)
}
Write-Host ""

Write-Host "[3/3] Verification"
$providersResponse = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/admin/feed-providers" -Headers $headers
$remainingEnabled = @($providersResponse.items | Where-Object { $_.id -like "mercadolibre_*_direct_v1" -and $_.enabled -eq $true })
[pscustomobject]@{
  updated = $updated
  remainingEnabled = $remainingEnabled.Count
} | ConvertTo-Json -Depth 5

if ($remainingEnabled.Count -gt 0) {
  Write-Warning "Some Mercado Libre Stage 56 providers are still enabled."
  exit 1
}

Write-Host "Stage 56b Mercado Libre providers disabled."
