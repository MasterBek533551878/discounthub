param(
  [string]$ApiBaseUrl = "http://127.0.0.1:8000",
  [string]$DbPath = "backend/data/discounthub.sqlite3",
  [switch]$Apply,
  [switch]$Sync,
  [int]$TimeoutSeconds = 90
)

$ErrorActionPreference = "Stop"

Write-Host "== DiscountHub Stage 73: simplify eBay marketplaces =="
Write-Host "API: $ApiBaseUrl"
Write-Host "DB : $DbPath"
Write-Host "Apply: $Apply"
Write-Host "Sync : $Sync"
Write-Host ""

try {
  $health = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/health" -TimeoutSec 10
  Write-Host "Backend health: $($health.status) ($($health.service))"
} catch {
  Write-Warning "Backend health check failed. DB cleanup can still run, but sync/facets require backend."
}

$applyValue = if ($Apply) { "1" } else { "0" }
$script = @'
import os
import shutil
import sqlite3
from datetime import datetime

DB_PATH = os.environ.get("DH_DB_PATH", "backend/data/discounthub.sqlite3")
APPLY = os.environ.get("DH_APPLY", "0") == "1"

ALLOWED_EBAY_PLATFORMS = {"ebay us", "ebay es", "ebay motors_us"}
LEGACY_EMPTY_MARKETPLACES = {"amazon", "aliexpress", "alibaba", "ebay", "ebay ca"}
ALLOWED_MARKETPLACE_IDS = ("MARKETPLACE_ID=EBAY_US", "MARKETPLACE_ID=EBAY_ES", "MARKETPLACE_ID=EBAY_MOTORS_US")

if not os.path.exists(DB_PATH):
    raise SystemExit(f"SQLite DB not found: {DB_PATH}")

con = sqlite3.connect(DB_PATH)
con.row_factory = sqlite3.Row

providers = con.execute(
    "SELECT id, name, url, enabled FROM feed_providers WHERE adapter='ebay_browse_api' ORDER BY id"
).fetchall()
providers_to_disable = []
providers_allowed = []
for row in providers:
    url_upper = (row["url"] or "").upper()
    if any(marker in url_upper for marker in ALLOWED_MARKETPLACE_IDS):
        providers_allowed.append(row["id"])
    else:
        providers_to_disable.append(row["id"])

unsupported_ebay_count = con.execute(
    """
    SELECT COUNT(*) AS total
    FROM deals
    WHERE LOWER(COALESCE(platform, '')) LIKE 'ebay%'
      AND LOWER(COALESCE(platform, '')) NOT IN ('ebay us', 'ebay es', 'ebay motors_us')
    """
).fetchone()["total"]
legacy_count = con.execute(
    f"""
    SELECT COUNT(*) AS total
    FROM deals
    WHERE LOWER(COALESCE(platform, '')) IN ({','.join('?' for _ in LEGACY_EMPTY_MARKETPLACES)})
    """,
    tuple(sorted(LEGACY_EMPTY_MARKETPLACES)),
).fetchone()["total"]
motors_count = con.execute(
    "SELECT COUNT(*) AS total FROM deals WHERE LOWER(COALESCE(platform, '')) = 'ebay motors_us'"
).fetchone()["total"]

print("eBay providers total:", len(providers))
print("eBay providers kept enabled/allowed:", len(providers_allowed))
print("eBay providers to disable:", len(providers_to_disable))
print("Unsupported regional eBay deals to delete:", unsupported_ebay_count)
print("Legacy empty marketplace deals to delete:", legacy_count)
print("eBay Motors deals to relabel as eBay US:", motors_count)

if not APPLY:
    print("DRY RUN ONLY. Re-run with -Apply to make changes.")
    con.close()
    raise SystemExit(0)

backup_path = f"{DB_PATH}.before_stage73_simplify_ebay_{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
shutil.copy2(DB_PATH, backup_path)
print("Backup:", backup_path)

now = datetime.utcnow().isoformat() + "Z"
for provider_id in providers_to_disable:
    con.execute(
        "UPDATE feed_providers SET enabled=0, updated_at=? WHERE id=?",
        (now, provider_id),
    )

# Remove old regional eBay rows that caused bad UX in browser clicks.
deleted_regional = con.execute(
    """
    DELETE FROM deals
    WHERE LOWER(COALESCE(platform, '')) LIKE 'ebay%'
      AND LOWER(COALESCE(platform, '')) NOT IN ('ebay us', 'ebay es', 'ebay motors_us')
    """
).rowcount

# Remove tiny legacy direct placeholders that look like empty stores in filters.
deleted_legacy = con.execute(
    f"""
    DELETE FROM deals
    WHERE LOWER(COALESCE(platform, '')) IN ({','.join('?' for _ in LEGACY_EMPTY_MARKETPLACES)})
    """,
    tuple(sorted(LEGACY_EMPTY_MARKETPLACES)),
).rowcount

# Group eBay Motors under eBay US in the customer-facing catalogue.
updated_motors = con.execute(
    "UPDATE deals SET platform='eBay US' WHERE LOWER(COALESCE(platform, '')) = 'ebay motors_us'"
).rowcount

con.commit()
print("Disabled regional eBay providers:", len(providers_to_disable))
print("Deleted unsupported regional eBay deals:", deleted_regional)
print("Deleted legacy empty marketplace deals:", deleted_legacy)
print("Relabeled eBay Motors deals:", updated_motors)
con.close()
'@

$env:DH_DB_PATH = $DbPath
$env:DH_APPLY = $applyValue
$script | python
Remove-Item Env:DH_DB_PATH -ErrorAction SilentlyContinue
Remove-Item Env:DH_APPLY -ErrorAction SilentlyContinue

if (-not $Apply) {
  Write-Host ""
  Write-Host "Stage 73 dry run completed."
  exit 0
}

if ($Sync) {
  $envFile = "backend/.env"
  if (-not (Test-Path $envFile)) {
    throw "backend/.env was not found; sync needs ADMIN_API_TOKEN."
  }
  $adminToken = ((Get-Content $envFile | Where-Object { $_ -match '^ADMIN_API_TOKEN=' }) -replace '^ADMIN_API_TOKEN=', '').Trim()
  if (-not $adminToken) {
    throw "ADMIN_API_TOKEN is missing in backend/.env."
  }

  $providersJson = @'
import json
import sqlite3
con = sqlite3.connect("backend/data/discounthub.sqlite3")
con.row_factory = sqlite3.Row
rows = con.execute("""
    SELECT id
    FROM feed_providers
    WHERE adapter='ebay_browse_api'
      AND enabled=1
      AND (
        UPPER(url) LIKE '%MARKETPLACE_ID=EBAY_US%'
        OR UPPER(url) LIKE '%MARKETPLACE_ID=EBAY_ES%'
        OR UPPER(url) LIKE '%MARKETPLACE_ID=EBAY_MOTORS_US%'
      )
    ORDER BY id
""").fetchall()
print(json.dumps([row["id"] for row in rows]))
con.close()
'@ | python
  $providers = $providersJson | ConvertFrom-Json

  Write-Host ""
  Write-Host "Syncing allowed eBay providers: $($providers.Count)"
  $ok = 0
  $failed = 0
  foreach ($providerId in $providers) {
    Write-Host "Sync: $providerId"
    try {
      $result = Invoke-RestMethod `
        -Method Post `
        -Headers @{ "X-Admin-Token" = $adminToken } `
        -Uri "$ApiBaseUrl/admin/feed-providers/$providerId/sync?timeout_seconds=$TimeoutSeconds" `
        -TimeoutSec ($TimeoutSeconds + 15)
      Write-Host "  OK imported=$($result.importedCount) deals=$($result.dealCount)"
      $ok += 1
    } catch {
      Write-Warning "  FAILED: $($_.Exception.Message)"
      $failed += 1
    }
  }
  Write-Host "Sync summary: ok=$ok failed=$failed"
}

Write-Host ""
try {
  Write-Host "Live facets after Stage 73:"
  $facets = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals/facets" -TimeoutSec 30
  Write-Host "Total deals: $($facets.total)"
  $facets.marketplaces | Select-Object -First 20 | Format-Table -AutoSize
} catch {
  Write-Warning "Could not read facets: $($_.Exception.Message)"
}

Write-Host "Stage 73 completed."
