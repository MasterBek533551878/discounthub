param(
  [string]$ApiBaseUrl = "http://127.0.0.1:8000",
  [string]$AdvertiserName = "Kinguin"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "== DiscountHub Stage 92 Kinguin audit =="
Write-Host "API: $ApiBaseUrl"
Write-Host "Advertiser query: $AdvertiserName"
Write-Host ""

Write-Host "[1/4] Health"
Invoke-RestMethod -Uri "$ApiBaseUrl/health" -Method Get | ConvertTo-Json -Depth 8
Write-Host ""

Write-Host "[2/4] Refresh Awin promotions"
try {
  Invoke-RestMethod `
    -Uri "$ApiBaseUrl/admin/promotions/awin/sync" `
    -Method Post `
    -Headers @{ "X-Admin-Token" = "dev-local-admin-token" } | ConvertTo-Json -Depth 8
} catch {
  Write-Host "Awin sync failed or admin token is different. Continuing with current /promotions data."
  Write-Host $_.Exception.Message
}
Write-Host ""

Write-Host "[3/4] Promotions matching Kinguin"
$encoded = [System.Uri]::EscapeDataString($AdvertiserName)
$promos = Invoke-RestMethod -Uri "$ApiBaseUrl/promotions?q=$encoded&page_size=20&sort=featured" -Method Get
$promos | ConvertTo-Json -Depth 8
Write-Host ""

Write-Host "[4/4] Local SQLite product deals matching Kinguin"
$repoRoot = Split-Path -Parent $PSScriptRoot
$dbPath = Join-Path $repoRoot "backend\data\discounthub.sqlite3"
if (-not (Test-Path $dbPath)) {
  Write-Host "SQLite DB not found: $dbPath"
  exit 0
}

$python = Join-Path $repoRoot "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
  $python = "py"
}

$env:DISCOUNTHUB_KINGUIN_DB = $dbPath
$env:DISCOUNTHUB_KINGUIN_QUERY = $AdvertiserName
@'
import os
import sqlite3

query = os.environ.get("DISCOUNTHUB_KINGUIN_QUERY", "Kinguin")
db_path = os.environ["DISCOUNTHUB_KINGUIN_DB"]
needle = f"%{query.lower()}%"

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
rows = cur.execute(
    """
    SELECT id, title, platform, category, provider_id, old_price, current_price, currency, discount_percent
    FROM deals
    WHERE lower(platform) LIKE ?
       OR lower(provider_id) LIKE ?
       OR lower(title) LIKE ?
    ORDER BY updated_at DESC
    LIMIT 20
    """,
    (needle, needle, needle),
).fetchall()

print(f"Matched product deals: {len(rows)}")
for row in rows:
    print(dict(row))
'@ | & $python -

Write-Host ""
Write-Host "Kinguin audit completed."
