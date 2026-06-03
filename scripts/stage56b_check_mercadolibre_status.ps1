param(
  [string]$ApiBaseUrl = "http://127.0.0.1:8000",
  [string]$AdminToken = "dev-local-admin-token"
)

$ErrorActionPreference = "Stop"
$headers = @{ "X-Admin-Token" = $AdminToken }

Write-Host "== DiscountHub Stage 56b Mercado Libre status check =="
Write-Host "API: $ApiBaseUrl"
Write-Host ""

Write-Host "[1/3] Health"
$health = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/health"
$health | ConvertTo-Json -Depth 6
Write-Host ""

Write-Host "[2/3] Mercado Libre providers"
$providersResponse = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/admin/feed-providers" -Headers $headers
$providers = @($providersResponse.items | Where-Object { $_.id -like "mercadolibre_*_direct_v1" })
[pscustomobject]@{
  total = $providers.Count
  enabled = @($providers | Where-Object { $_.enabled -eq $true }).Count
  statuses = @($providers | Select-Object id, enabled, adapter, monetizationMode, lastStatus, lastImportedCount, lastMessage | Select-Object -First 16)
} | ConvertTo-Json -Depth 10
Write-Host ""

Write-Host "[3/3] Recent Mercado Libre sync runs"
try {
  $runs = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/admin/feed-providers/sync-runs?limit=20" -Headers $headers
  $meliRuns = @($runs.items | Where-Object { $_.providerId -like "mercadolibre_*_direct_v1" })
  [pscustomobject]@{
    totalReturned = $runs.items.Count
    mercadoLibreRuns = $meliRuns.Count
    recent = @($meliRuns | Select-Object providerId, status, importedCount, message, createdAt | Select-Object -First 10)
  } | ConvertTo-Json -Depth 10
} catch {
  Write-Warning "Could not read sync runs: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "Stage 56b status check completed."
