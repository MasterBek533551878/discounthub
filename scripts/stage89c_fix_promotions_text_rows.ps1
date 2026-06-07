param(
  [string]$BackendDir = "backend"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()

Write-Host "== DiscountHub Stage 89c promotions text row cleanup =="

$Root = (Resolve-Path ".").Path
$BackendPath = Join-Path $Root $BackendDir
$PythonExe = Join-Path $BackendPath ".venv\Scripts\python.exe"

if (!(Test-Path $PythonExe)) {
  throw "Python venv not found: $PythonExe"
}

$code = @'
from app.db.database import get_connection
from app.services.promotions_service import clean_promotion_text

fields = ["title", "description", "store", "discount_text", "code"]
changed_rows = 0
changed_fields = 0

with get_connection() as conn:
    rows = conn.execute("SELECT id, title, description, store, discount_text, code FROM promotions").fetchall()
    for row in rows:
        updates = {}
        for field in fields:
            old = row[field]
            if old is None:
                continue
            new = clean_promotion_text(str(old))
            if new != old:
                updates[field] = new
        if updates:
            changed_rows += 1
            changed_fields += len(updates)
            assignments = ", ".join([f"{field} = ?" for field in updates.keys()])
            params = [*updates.values(), row["id"]]
            conn.execute(f"UPDATE promotions SET {assignments} WHERE id = ?", params)
    conn.commit()

print(f"Changed rows: {changed_rows}")
print(f"Changed fields: {changed_fields}")
print("Cleaner check:", clean_promotion_text("â\x82¬200 OFF"), clean_promotion_text("â¬300 OFF"))
'@

Push-Location $BackendPath
try {
  $code | & $PythonExe -
}
finally {
  Pop-Location
}
