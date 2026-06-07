param(
  [string]$ApiBaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "== DiscountHub Stage 92 multi-select filters check =="
Write-Host "API: $ApiBaseUrl"
Write-Host ""

Write-Host "[1/4] Health"
$health = Invoke-RestMethod -Uri "$ApiBaseUrl/health" -Method Get
$health | ConvertTo-Json -Depth 8
Write-Host ""

Write-Host "[2/4] Deals: AliExpress + eBay"
$marketplaces = Invoke-RestMethod -Uri "$ApiBaseUrl/deals?platform=AliExpress,eBay&page_size=10&sort=newest" -Method Get
$marketplaces | ConvertTo-Json -Depth 8
Write-Host ""

Write-Host "[3/4] Deals: Electronics + Fashion"
$categories = Invoke-RestMethod -Uri "$ApiBaseUrl/deals?category=Electronics,Fashion&page_size=10&sort=newest" -Method Get
$categories | ConvertTo-Json -Depth 8
Write-Host ""

Write-Host "[4/4] Promotions: AliExpress PL + Navimow FR"
$promos = Invoke-RestMethod -Uri "$ApiBaseUrl/promotions?store=AliExpress%20PL,Navimow%20FR&page_size=10&sort=featured" -Method Get
$promos | ConvertTo-Json -Depth 8
Write-Host ""

Write-Host "Stage 92 check completed."
