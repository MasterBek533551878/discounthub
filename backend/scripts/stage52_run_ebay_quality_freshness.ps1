param(
  [string]$BaseUrl = "http://127.0.0.1:8000",
  [string]$AdminToken = "",
  [int]$TimeoutSeconds = 35,
  [int]$MinDiscount = 15,
  [int]$MaxAgeHours = 72,
  [switch]$SyncFirst,
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$BackendDir = Split-Path -Parent $PSScriptRoot
Set-Location $BackendDir

if (-not $AdminToken) {
  $envPath = Join-Path $BackendDir ".env"
  if (Test-Path $envPath) {
    $line = Get-Content $envPath | Where-Object { $_ -match "^ADMIN_API_TOKEN=" } | Select-Object -First 1
    if ($line) {
      $AdminToken = ($line -replace "^ADMIN_API_TOKEN=", "").Trim()
    }
  }
}
if (-not $AdminToken) { $AdminToken = "dev-local-admin-token" }
$headers = @{ "X-Admin-Token" = $AdminToken }

Write-Host "Stage 52: hardening eBay provider filters..."
python .\scripts\stage52_harden_ebay_filters.py --min-discount $MinDiscount

if ($SyncFirst) {
  Write-Host "Stage 52: syncing enabled providers from backend before cleanup..."
  $sync = Invoke-RestMethod -Uri "$BaseUrl/admin/feed-providers/sync-all?timeout_seconds=$TimeoutSeconds" -Method Post -Headers $headers
  $sync | Format-List
}

Write-Host "Stage 52: cleaning low-quality/stale eBay deals..."
$argsList = @(
  ".\scripts\stage52_quality_freshness_cleanup.py",
  "--min-discount", "$MinDiscount",
  "--max-age-hours", "$MaxAgeHours"
)
if ($DryRun) { $argsList += "--dry-run" }
python @argsList

Write-Host "Stage 52: quality check..."
python .\scripts\stage52_check_quality.py

Write-Host "Stage 52 completed."
