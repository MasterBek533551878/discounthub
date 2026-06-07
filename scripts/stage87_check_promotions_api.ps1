param(
  [string]$ApiBaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

Write-Host "== DiscountHub Stage 87 promotions API check ==" -ForegroundColor Cyan
Write-Host "API: $ApiBaseUrl"

Write-Host "`n[1/3] Health"
$health = Invoke-RestMethod -Uri "$ApiBaseUrl/health" -Method Get
$health | ConvertTo-Json -Depth 8

Write-Host "`n[2/3] Promotions list"
$promotions = Invoke-RestMethod -Uri "$ApiBaseUrl/promotions?page_size=5" -Method Get
$promotions | ConvertTo-Json -Depth 10

Write-Host "`n[3/3] Promo filters"
$coupons = Invoke-RestMethod -Uri "$ApiBaseUrl/promotions?type=coupon&page_size=5" -Method Get
Write-Host "Coupon total: $($coupons.total)"

Write-Host "`nStage 87 check completed." -ForegroundColor Green
