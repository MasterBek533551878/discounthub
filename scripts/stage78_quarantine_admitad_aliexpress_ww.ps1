param(
  [string]$Server = "ubuntu@51.68.46.242",
  [string]$ProviderId = "admitad_6115_aliexpress_ww_v1",
  [switch]$Apply
)

$ErrorActionPreference = "Stop"

Write-Host "== DiscountHub Stage 78: Quarantine broken Admitad AliExpress WW =="
Write-Host "Server: $Server"
Write-Host "Provider: $ProviderId"
Write-Host "Mode: $(if ($Apply) { 'apply' } else { 'dry-run' })"
Write-Host ""

$localPy = Join-Path $env:TEMP "stage78_quarantine_admitad_aliexpress_ww.py"
$remotePy = "/tmp/stage78_quarantine_admitad_aliexpress_ww.py"

@'
import argparse
import sqlite3
from datetime import datetime, timezone

parser = argparse.ArgumentParser()
parser.add_argument("--db", default="/opt/discounthub/backend/data/discounthub.sqlite3")
parser.add_argument("--provider-id", required=True)
parser.add_argument("--apply", action="store_true")
args = parser.parse_args()

provider_id = args.provider_id
now = datetime.now(timezone.utc).isoformat()

conn = sqlite3.connect(args.db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

provider = cur.execute(
    "SELECT id, enabled, last_status, last_imported_count FROM feed_providers WHERE id = ?",
    (provider_id,),
).fetchone()

count_before = cur.execute(
    "SELECT COUNT(*) AS c FROM deals WHERE provider_id = ?",
    (provider_id,),
).fetchone()["c"]

print("Provider before:", dict(provider) if provider else None)
print("Provider deals before:", count_before)

if not args.apply:
    print("Dry-run only. No rows deleted. Add -Apply to apply quarantine.")
    conn.close()
    raise SystemExit(0)

cur.execute(
    "UPDATE feed_providers SET enabled = 0, updated_at = ? WHERE id = ?",
    (now, provider_id),
)
updated_providers = cur.rowcount

cur.execute(
    "DELETE FROM deals WHERE provider_id = ?",
    (provider_id,),
)
deleted_deals = cur.rowcount
conn.commit()

provider_after = cur.execute(
    "SELECT id, enabled, last_status, last_imported_count FROM feed_providers WHERE id = ?",
    (provider_id,),
).fetchone()

count_after = cur.execute(
    "SELECT COUNT(*) AS c FROM deals WHERE provider_id = ?",
    (provider_id,),
).fetchone()["c"]

total_after = cur.execute("SELECT COUNT(*) AS c FROM deals").fetchone()["c"]

print("Updated providers:", updated_providers)
print("Deleted deals:", deleted_deals)
print("Provider after:", dict(provider_after) if provider_after else None)
print("Provider deals after:", count_after)
print("Total deals after:", total_after)

conn.close()
'@ | Set-Content -Encoding UTF8 $localPy

scp $localPy "$Server`:$remotePy"
if ($LASTEXITCODE -ne 0) {
  throw "scp failed with exit code $LASTEXITCODE"
}

$applyArg = if ($Apply) { " --apply" } else { "" }
$remoteCommand = "python3 $remotePy --provider-id '$ProviderId'$applyArg"

if ($Apply) {
  $remoteCommand += " && sudo systemctl restart discounthub && sleep 2 && curl -s https://api.discounthub.uz/health"
}

ssh $Server $remoteCommand
if ($LASTEXITCODE -ne 0) {
  throw "remote quarantine command failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "Stage 78 quarantine script completed."
