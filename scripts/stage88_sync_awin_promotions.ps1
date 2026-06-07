param(
  [string]$ApiBaseUrl = "http://127.0.0.1:8000",
  [string]$AdminToken = "",
  [int]$PageSize = 100,
  [int]$MaxPages = 5,
  [string]$Membership = "joined",
  [string]$Status = "active",
  [string]$Type = "all"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

function Read-EnvValue([string]$Path, [string]$Name) {
  if (-not (Test-Path $Path)) { return "" }
  $line = Get-Content -LiteralPath $Path -Encoding UTF8 |
    Where-Object { $_ -match "^\s*$([regex]::Escape($Name))\s*=" } |
    Select-Object -First 1
  if (-not $line) { return "" }
  return (($line -split "=", 2)[1]).Trim().Trim('"').Trim("'")
}

if ([string]::IsNullOrWhiteSpace($AdminToken)) {
  $AdminToken = Read-EnvValue -Path "backend/.env" -Name "ADMIN_API_TOKEN"
}
if ([string]::IsNullOrWhiteSpace($AdminToken)) {
  $AdminToken = "dev-local-admin-token"
}

Write-Host "== DiscountHub Stage 88 Awin promotions sync =="
Write-Host "API: $ApiBaseUrl"
Write-Host ""

Write-Host "[1/4] Health"
$health = Invoke-RestMethod -Uri "$ApiBaseUrl/health" -Method Get
$health | ConvertTo-Json -Depth 6
Write-Host ""

Write-Host "[2/4] Sync Awin Offers / My Offers"
$body = @{
  membership = $Membership
  status = $Status
  type = $Type
  pageSize = $PageSize
  maxPages = $MaxPages
} | ConvertTo-Json -Depth 6

$sync = Invoke-RestMethod `
  -Uri "$ApiBaseUrl/admin/promotions/awin/sync" `
  -Method Post `
  -Headers @{ "X-Admin-Token" = $AdminToken } `
  -ContentType "application/json" `
  -Body $body
$sync | ConvertTo-Json -Depth 8
Write-Host ""

Write-Host "[3/4] Promotions list sample"
$list = Invoke-RestMethod -Uri "$ApiBaseUrl/promotions?page_size=10&sort=newest" -Method Get
$list | ConvertTo-Json -Depth 10
Write-Host ""

Write-Host "[4/4] Coupon sample"
$coupons = Invoke-RestMethod -Uri "$ApiBaseUrl/promotions?type=coupon&page_size=5&sort=newest" -Method Get
$coupons | ConvertTo-Json -Depth 10
Write-Host ""

Write-Host "Stage 88 Awin promotions sync completed."
