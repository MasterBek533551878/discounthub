param(
  [string]$DbPath = "backend/data/discounthub.sqlite3",
  [switch]$Apply
)

$ErrorActionPreference = "Stop"

function Invoke-ProjectPython {
  param([string[]]$Arguments, [string]$StdinText = $null)

  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($py) {
    if ($null -ne $StdinText) { $StdinText | & py -3 @Arguments } else { & py -3 @Arguments }
    return
  }

  $python = Get-Command python -ErrorAction SilentlyContinue
  if (-not $python) { throw "Python was not found. Install Python or use the Python launcher 'py'." }
  if ($null -ne $StdinText) { $StdinText | & python @Arguments } else { & python @Arguments }
}

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$db = Join-Path $root $DbPath
if (-not (Test-Path $db)) {
  throw "SQLite DB not found: $db"
}

Write-Host "== DiscountHub Stage 76: Admitad default-link cleanup =="
Write-Host "DB: $db"
if (-not $Apply) {
  Write-Host "Mode: dry-run. Add -Apply to delete bad rows after review."
} else {
  Write-Host "Mode: APPLY. A timestamped .bak copy will be created first."
}

$script = @'
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

db_path = Path(sys.argv[1])
apply = sys.argv[2].lower() == "true"

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
try:
    where = """
    (
        LOWER(COALESCE(provider_id, '')) LIKE 'admitad_%'
        OR LOWER(COALESCE(id, '')) LIKE 'admitad_%'
        OR LOWER(COALESCE(platform, '')) LIKE '%aliexpress%'
    )
    AND (
        LOWER(COALESCE(affiliate_url, '')) LIKE '%rzekl.com/g/%'
        OR LOWER(COALESCE(affiliate_url, '')) LIKE '%rztekl.com/g/%'
        OR LOWER(COALESCE(affiliate_url, '')) LIKE '%ad.admitad.com/g/%'
    )
    AND LOWER(COALESCE(affiliate_url, '')) NOT LIKE '%ulp=%'
    """
    rows = conn.execute(
        f"""
        SELECT id, title, platform, provider_id, product_url, affiliate_url
        FROM deals
        WHERE {where}
        ORDER BY updated_at DESC
        LIMIT 30
        """
    ).fetchall()
    count = conn.execute(f"SELECT COUNT(*) FROM deals WHERE {where}").fetchone()[0]

    print(f"Bad Admitad default-link rows: {count}")
    for row in rows[:10]:
        print(f"- {row['id']} | {row['platform']} | {row['title'][:90]}")
        print(f"  affiliate_url={row['affiliate_url']}")
        print(f"  product_url={row['product_url']}")

    if not apply:
        print("Dry-run only. No rows deleted.")
        return_code = 0
    elif count == 0:
        print("Nothing to delete.")
        return_code = 0
    else:
        backup = db_path.with_suffix(db_path.suffix + f".stage76_backup_{datetime.now().strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(db_path, backup)
        conn.execute(f"DELETE FROM deals WHERE {where}")
        conn.commit()
        print(f"Deleted rows: {count}")
        print(f"Backup: {backup}")
        return_code = 0
finally:
    conn.close()

raise SystemExit(return_code)
'@

Invoke-ProjectPython -Arguments @("-", $db, ($(if ($Apply) { "true" } else { "false" }))) -StdinText $script
