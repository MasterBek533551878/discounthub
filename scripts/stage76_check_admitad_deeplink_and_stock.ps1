param(
  [string]$BackendPath = "backend"
)

$ErrorActionPreference = "Stop"

Write-Host "== DiscountHub Stage 76: Admitad deeplink + stock-filter check =="

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$backend = Join-Path $root $BackendPath
if (-not (Test-Path $backend)) {
  throw "Backend path not found: $backend"
}

function Get-ProjectPythonCommand {
  $winVenv = Join-Path $backend ".venv\Scripts\python.exe"
  if (Test-Path $winVenv) {
    return @{ Type = "exe"; Value = $winVenv }
  }

  $linuxVenv = Join-Path $backend ".venv/bin/python"
  if (Test-Path $linuxVenv) {
    return @{ Type = "exe"; Value = $linuxVenv }
  }

  $python = Get-Command python -ErrorAction SilentlyContinue
  if ($python) {
    return @{ Type = "exe"; Value = $python.Source }
  }

  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($py) {
    return @{ Type = "py"; Value = "py" }
  }

  throw "Python was not found. Install Python or create backend/.venv."
}

$script:ProjectPython = Get-ProjectPythonCommand
Write-Host "Python: $($script:ProjectPython.Value)"

function Invoke-ProjectPython {
  param([string[]]$Arguments, [string]$StdinText = $null)

  if ($script:ProjectPython.Type -eq "py") {
    if ($null -ne $StdinText) {
      $StdinText | & py -3 @Arguments
    } else {
      & py -3 @Arguments
    }
  } else {
    if ($null -ne $StdinText) {
      $StdinText | & $script:ProjectPython.Value @Arguments
    } else {
      & $script:ProjectPython.Value @Arguments
    }
  }

  if ($LASTEXITCODE -ne 0) {
    throw "Python command failed with exit code $LASTEXITCODE"
  }
}

Push-Location $backend
try {
  Write-Host "[1/2] Python compile check"
  Invoke-ProjectPython -Arguments @(
    "-m", "py_compile",
    "app/services/feed_adapters.py",
    "app/services/ebay_browse_service.py",
    "app/services/feed_import_service.py",
    "app/services/awin_feed_list_service.py"
  )

  Write-Host "[2/2] Unit smoke check"
  $script = @'
from app.services.feed_adapters import FeedAdapterService
from app.services.ebay_browse_service import EbayBrowseService
from app.services.feed_import_service import FeedImportService
from app.services.awin_feed_list_service import AwinFeedListService

adapter = FeedAdapterService()
item = {
    "name": "AliExpress test item",
    "gotolink": "https://rzekl.com/g/1e8d1144947bb865423f16525dc3e8/",
    "url": "https://www.aliexpress.com/item/1005006789012345.html?spm=test",
    "picture": "https://example.com/image.jpg",
    "price": "10",
    "oldprice": "20",
}
normalized = adapter._normalize_admitad(item)
assert normalized["productUrl"] == "https://www.aliexpress.com/item/1005006789012345.html", normalized
assert normalized["affiliateUrl"].startswith("https://ad.admitad.com/g/1e8d1144947bb865423f16525dc3e8/"), normalized["affiliateUrl"]
assert "ulp=" in normalized["affiliateUrl"] and "1005006789012345.html" in normalized["affiliateUrl"], normalized["affiliateUrl"]
assert adapter._build_admitad_deeplink("https://example.com/product/1", "https://www.aliexpress.com/item/1.html") == "https://example.com/product/1"

ebay = EbayBrowseService()
assert ebay._is_unavailable_item({"estimatedAvailabilities": [{"estimatedAvailabilityStatus": "OUT_OF_STOCK"}]}) is True
assert ebay._is_unavailable_item({"estimatedAvailabilities": [{"estimatedAvailabilityStatus": "IN_STOCK"}]}) is False
assert ebay._is_unavailable_item({"estimatedAvailabilities": [{"estimatedAvailableQuantity": 0}]}) is True

importer = FeedImportService()
assert importer._raw_is_out_of_stock({"availability": "out of stock"}) is True
assert importer._raw_is_out_of_stock({"g:availability": "out of stock"}) is True
assert importer._raw_is_out_of_stock({"availability": "in stock"}) is False

awin = AwinFeedListService()
assert awin._is_out_of_stock({"g:availability": "out of stock"}) is True
assert awin._is_out_of_stock({"availability": "in stock"}) is False

print("Stage 76 smoke checks passed.")
'@
  Invoke-ProjectPython -Arguments @("-") -StdinText $script
} finally {
  Pop-Location
}

Write-Host "Stage 76 check completed successfully."
