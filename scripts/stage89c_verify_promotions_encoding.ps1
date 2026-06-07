param(
  [string]$ApiBaseUrl = "http://127.0.0.1:8000",
  [string]$BackendDir = "backend"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()

Write-Host "== DiscountHub Stage 89c promotions encoding verify =="
Write-Host "API: $ApiBaseUrl"

$Root = (Resolve-Path ".").Path
$BackendPath = Join-Path $Root $BackendDir
$PythonExe = Join-Path $BackendPath ".venv\Scripts\python.exe"

if (!(Test-Path $PythonExe)) {
  throw "Python venv not found: $PythonExe"
}

$env:DISCOUNTHUB_VERIFY_API_BASE_URL = $ApiBaseUrl
$code = @'
import json
import os
import urllib.parse
import urllib.request

base = os.environ["DISCOUNTHUB_VERIFY_API_BASE_URL"].rstrip("/")
url = base + "/promotions?" + urllib.parse.urlencode({"q": "Navimow", "page_size": 10, "sort": "newest"})
raw = urllib.request.urlopen(url, timeout=20).read().decode("utf-8")
data = json.loads(raw)
print("total:", data.get("total"))
for item in data.get("items", []):
    print(item.get("id"), "|", item.get("discountText"), "|", item.get("description"))
    text = f"{item.get('discountText','')} {item.get('description','')}"
    if "â" in text or "Â" in text or "ï¼" in text:
        raise SystemExit("Mojibake still visible in API response")
print("Encoding check OK")
'@

$code | & $PythonExe -
