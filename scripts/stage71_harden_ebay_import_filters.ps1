param(
  [string]$ApiBaseUrl = "http://127.0.0.1:8000",
  [string]$DbPath = "backend/data/discounthub.sqlite3",
  [switch]$Apply,
  [switch]$Sync,
  [int]$LimitProviders = 0,
  [int]$TimeoutSeconds = 60
)

$ErrorActionPreference = "Stop"

Write-Host "== DiscountHub Stage 71: harden eBay import filters =="
Write-Host "API: $ApiBaseUrl"
Write-Host "DB : $DbPath"
Write-Host "Apply: $Apply"
Write-Host "Sync : $Sync"
Write-Host "Provider limit: $LimitProviders"
Write-Host ""

try {
  $health = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/health" -TimeoutSec 10
  Write-Host "Backend health: $($health.status) ($($health.service))"
} catch {
  Write-Warning "Backend health check failed. DB update can still run, but sync requires backend."
}

$applyValue = if ($Apply) { "1" } else { "0" }
$script = @'
import os
import shutil
import sqlite3
from datetime import datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

DB_PATH = os.environ.get("DH_DB_PATH", "backend/data/discounthub.sqlite3")
APPLY = os.environ.get("DH_APPLY", "0") == "1"
STRICT_PARAMS = {
    "min_discount": "20",
    "max_discount": "85",
    "require_fixed_price": "true",
    "require_image": "true",
    "require_clickable_url": "true",
    "min_seller_feedback_percent": "90",
    "min_seller_feedback_score": "5",
}

def harden_url(url: str) -> str:
    parts = urlsplit(url)
    pairs = parse_qsl(parts.query, keep_blank_values=True)
    params = dict(pairs)
    for key, value in STRICT_PARAMS.items():
        current = str(params.get(key, "")).strip()
        if not current:
            params[key] = value
        elif key in {"min_discount", "min_seller_feedback_percent", "min_seller_feedback_score"}:
            try:
                if float(current) < float(value):
                    params[key] = value
            except ValueError:
                params[key] = value
        elif key == "max_discount":
            try:
                if float(current) > float(value):
                    params[key] = value
            except ValueError:
                params[key] = value
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(params, doseq=True), parts.fragment))

if not os.path.exists(DB_PATH):
    raise SystemExit(f"SQLite DB not found: {DB_PATH}")

con = sqlite3.connect(DB_PATH)
con.row_factory = sqlite3.Row
rows = con.execute(
    "SELECT id, name, url, enabled FROM feed_providers WHERE adapter='ebay_browse_api' ORDER BY id"
).fetchall()
print("eBay providers:", len(rows))
changed = []
for row in rows:
    new_url = harden_url(row["url"] or "")
    if new_url != (row["url"] or ""):
        changed.append((row["id"], row["url"], new_url))

existing_ebay = con.execute(
    """
    SELECT COUNT(*) AS total
    FROM deals
    WHERE LOWER(COALESCE(platform, '')) LIKE 'ebay%'
       OR LOWER(COALESCE(provider_id, '')) LIKE 'ebay_%'
    """
).fetchone()["total"]
print("Provider URLs to harden:", len(changed))
print("Existing eBay deals to purge before clean resync:", existing_ebay)

if not APPLY:
    print("DRY RUN ONLY. Re-run with -Apply to update provider URLs and delete old eBay deals.")
    con.close()
    raise SystemExit(0)

backup_path = f"{DB_PATH}.before_stage71_ebay_quality_{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
shutil.copy2(DB_PATH, backup_path)
print("Backup:", backup_path)

now = datetime.utcnow().isoformat() + "Z"
for provider_id, old_url, new_url in changed:
    con.execute(
        "UPDATE feed_providers SET url=?, updated_at=? WHERE id=?",
        (new_url, now, provider_id),
    )

deleted = con.execute(
    """
    DELETE FROM deals
    WHERE LOWER(COALESCE(platform, '')) LIKE 'ebay%'
       OR LOWER(COALESCE(provider_id, '')) LIKE 'ebay_%'
    """
).rowcount
con.commit()
print("Updated provider URLs:", len(changed))
print("Deleted old eBay deals:", deleted)
con.close()
'@

$env:DH_DB_PATH = $DbPath
$env:DH_APPLY = $applyValue
$script | python
Remove-Item Env:DH_DB_PATH -ErrorAction SilentlyContinue
Remove-Item Env:DH_APPLY -ErrorAction SilentlyContinue

if (-not $Apply) {
  Write-Host ""
  Write-Host "Stage 71 dry run completed."
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
rows = con.execute("SELECT id FROM feed_providers WHERE adapter='ebay_browse_api' AND enabled=1 ORDER BY id").fetchall()
print(json.dumps([row["id"] for row in rows]))
con.close()
'@ | python
  $providers = $providersJson | ConvertFrom-Json
  if ($LimitProviders -gt 0) {
    $providers = @($providers | Select-Object -First $LimitProviders)
  }

  Write-Host ""
  Write-Host "Syncing eBay providers: $($providers.Count)"
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
  Write-Host "Live facets after Stage 71:"
  $facets = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals/facets" -TimeoutSec 30
  Write-Host "Total deals: $($facets.total)"
  $facets.marketplaces | Select-Object -First 15 | Format-Table -AutoSize
} catch {
  Write-Warning "Could not read facets: $($_.Exception.Message)"
}

Write-Host "Stage 71 completed."
