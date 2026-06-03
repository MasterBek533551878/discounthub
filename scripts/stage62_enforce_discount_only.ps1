param(
  [string]$ApiBaseUrl = "http://127.0.0.1:8000",
  [string]$AdminToken = "",
  [string]$EnvPath = "backend/.env",
  [string]$DbPath = "backend/data/discounthub.sqlite3",
  [string]$ProviderId = "awin_feed_list",
  [int]$MaxFeeds = 20,
  [int]$MaxItemsPerFeed = 80,
  [int]$MinDiscountPercent = 1,
  [int]$TimeoutSeconds = 60,
  [switch]$SkipSync,
  [switch]$NoDbCleanup
)

$ErrorActionPreference = "Stop"

function Read-EnvValue {
  param([string]$Name, [string]$Path = "backend/.env")
  $fromProcess = [Environment]::GetEnvironmentVariable($Name)
  if (![string]::IsNullOrWhiteSpace($fromProcess)) { return $fromProcess }
  if (!(Test-Path $Path)) { return "" }
  $line = Get-Content -Path $Path -Encoding UTF8 | Where-Object { $_ -match "^$([regex]::Escape($Name))=" } | Select-Object -First 1
  if (!$line) { return "" }
  $value = [string]($line -replace "^$([regex]::Escape($Name))=", "")
  $value = $value.Trim()
  if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
    $value = $value.Substring(1, $value.Length - 2)
  }
  return $value
}

function Resolve-PythonExecutable {
  $localPython = Join-Path (Get-Location) "backend\.venv\Scripts\python.exe"
  if (Test-Path $localPython) { return $localPython }

  $commands = @("python", "py")
  foreach ($command in $commands) {
    $found = Get-Command $command -ErrorAction SilentlyContinue
    if ($found) { return $found.Source }
  }

  throw "Python executable not found. Expected backend\.venv\Scripts\python.exe or python in PATH."
}

function Invoke-ApiJson {
  param(
    [string]$Method,
    [string]$Uri,
    [hashtable]$Headers = @{},
    [object]$Body = $null,
    [int]$TimeoutSec = 30
  )
  if ($null -eq $Body) {
    return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $Headers -TimeoutSec $TimeoutSec
  }
  return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $Headers -ContentType "application/json" -Body ($Body | ConvertTo-Json -Depth 12) -TimeoutSec $TimeoutSec
}

if ([string]::IsNullOrWhiteSpace($AdminToken)) {
  $AdminToken = Read-EnvValue -Name "ADMIN_API_TOKEN" -Path $EnvPath
}
if ([string]::IsNullOrWhiteSpace($AdminToken)) { $AdminToken = "dev-local-admin-token" }
if ($TimeoutSeconds -gt 60) { $TimeoutSeconds = 60 }
if ($MinDiscountPercent -lt 1) { $MinDiscountPercent = 1 }

Write-Host "== DiscountHub Stage 62b: hard enforce discount-only catalogue =="
Write-Host "API: $ApiBaseUrl"
Write-Host "MinDiscountPercent: $MinDiscountPercent"
Write-Host "JoinedOnly: true"
Write-Host ""

$health = Invoke-ApiJson -Method Get -Uri "$ApiBaseUrl/health" -TimeoutSec 10
Write-Host "Backend health: $($health.status) ($($health.service))"

$headers = @{ "X-Admin-Token" = $AdminToken }
$providerUrl = "awin://feed-list?max_feeds=$MaxFeeds&max_items_per_feed=$MaxItemsPerFeed&min_discount_percent=$MinDiscountPercent&joined_only=true"
$provider = [ordered]@{
  id = $ProviderId
  name = "Awin Product Feed List - joined discount products"
  url = $providerUrl
  adapter = "awin_feed_list_api"
  enabled = $true
  replaceOnSync = $false
  monetizationMode = "affiliate"
}

Write-Host "[1/4] Upserting Awin provider in discount-only mode"
$result = Invoke-ApiJson -Method Post -Uri "$ApiBaseUrl/admin/feed-providers" -Headers $headers -Body $provider -TimeoutSec 30
Write-Host "Provider URL: $($result.url)"

if (!$SkipSync) {
  Write-Host ""
  Write-Host "[2/4] Syncing Awin discount rows"
  try {
    $sync = Invoke-ApiJson -Method Post -Uri "$ApiBaseUrl/admin/feed-providers/$ProviderId/sync?timeout_seconds=$TimeoutSeconds" -Headers $headers -TimeoutSec ($TimeoutSeconds + 20)
    Write-Host "Sync status: $($sync.status); imported=$($sync.importedCount); total=$($sync.dealCount)"
    if ($sync.message) { Write-Host "Message: $($sync.message)" }
  } catch {
    Write-Warning "Awin sync failed. Continuing to DB cleanup. If Awin has no discounted rows right now, this is acceptable."
    Write-Warning $_.Exception.Message
  }
} else {
  Write-Host ""
  Write-Host "[2/4] Sync skipped because -SkipSync was passed."
}

if (!$NoDbCleanup) {
  Write-Host ""
  Write-Host "[3/4] Removing non-discount rows from local SQLite DB"
  if (!(Test-Path $DbPath)) { throw "SQLite DB not found: $DbPath" }
  $pythonExe = Resolve-PythonExecutable
  Write-Host "Python: $pythonExe"
  $cleanupCode = @'
import os
import shutil
import sqlite3
from datetime import datetime

path = os.environ["DISCOUNTHUB_DB_PATH"]
min_discount = float(os.environ.get("DISCOUNTHUB_MIN_DISCOUNT", "1"))
stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
backup = f"{path}.stage62b_backup_{stamp}"
shutil.copy2(path, backup)

conn = sqlite3.connect(path)
cur = conn.cursor()
before = cur.execute("SELECT COUNT(*) FROM deals").fetchone()[0]
non_discount_before = cur.execute(
    """
    SELECT COUNT(*) FROM deals
    WHERE old_price <= current_price
       OR old_price <= 0
       OR current_price <= 0
       OR (((old_price - current_price) / old_price) * 100) < ?
    """,
    (min_discount,),
).fetchone()[0]
cur.execute(
    """
    DELETE FROM deals
    WHERE old_price <= current_price
       OR old_price <= 0
       OR current_price <= 0
       OR (((old_price - current_price) / old_price) * 100) < ?
    """,
    (min_discount,),
)
conn.commit()
after = cur.execute("SELECT COUNT(*) FROM deals").fetchone()[0]
by_mode = cur.execute(
    "SELECT COALESCE(monetization_mode, 'direct') AS mode, COUNT(*) FROM deals GROUP BY mode ORDER BY COUNT(*) DESC"
).fetchall()
by_platform = cur.execute(
    "SELECT platform, COUNT(*) FROM deals GROUP BY platform ORDER BY COUNT(*) DESC LIMIT 15"
).fetchall()
conn.close()
print(f"Backup created: {backup}")
print(f"Deals before       : {before}")
print(f"Non-discount before: {non_discount_before}")
print(f"Deals after        : {after}")
print(f"Deleted            : {before - after}")
print("By monetization mode:")
for row in by_mode:
    print(f"  {row[0]}: {row[1]}")
print("Top platforms after cleanup:")
for row in by_platform:
    print(f"  {row[0]}: {row[1]}")
'@
  $env:DISCOUNTHUB_DB_PATH = (Resolve-Path $DbPath).Path
  $env:DISCOUNTHUB_MIN_DISCOUNT = [string]$MinDiscountPercent
  & $pythonExe -c $cleanupCode
} else {
  Write-Host ""
  Write-Host "[3/4] DB cleanup skipped because -NoDbCleanup was passed."
}

Write-Host ""
Write-Host "[4/4] Public API check"
$facets = Invoke-ApiJson -Method Get -Uri "$ApiBaseUrl/deals/facets" -TimeoutSec 30
$page = Invoke-ApiJson -Method Get -Uri "$ApiBaseUrl/deals?page_size=50&sort=discount_desc" -TimeoutSec 30
$items = @($page.items)
$bad = @($items | Where-Object { $_.discountPercent -le 0 -or $_.oldPrice -le $_.currentPrice })
Write-Host "Facets total: $($facets.total)"
Write-Host "Page items  : $($items.Count)"
Write-Host "Bad rows    : $($bad.Count)"
Write-Host "Top marketplaces:"
@($facets.marketplaces) | Select-Object -First 20 id,count | Format-Table -AutoSize
Write-Host "Monetization modes:"
@($facets.monetizationModes) | Select-Object id,count | Format-Table -AutoSize
if ($bad.Count -gt 0) { throw "Public API still returned non-discount rows." }
Write-Host "OK: public catalogue is discount-only." -ForegroundColor Green
