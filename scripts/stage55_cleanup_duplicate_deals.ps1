param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")),
    [string]$ApiBaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

Write-Host "== DiscountHub Stage 55 duplicate/bad deals cleanup =="

$backendDir = Join-Path $ProjectRoot "backend"
$python = Join-Path $backendDir ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

Push-Location $backendDir
try {
    $env:PYTHONPATH = "."
    & $python "scripts\cleanup_duplicate_bad_deals.py"
    if ($LASTEXITCODE -ne 0) {
        throw "Cleanup script failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "Checking API after cleanup..."
$facets = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals/facets?currency=USD"
$defect = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals?q=defect&page_size=5&currency=USD"
$firstPage = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/deals?sort=discount_desc&page=1&page_size=50&currency=USD"

$seen = @{}
$dupes = @()
foreach ($item in $firstPage.items) {
    $key = (("{0}|{1}|{2}|{3:N2}|{4:N2}" -f $item.platform, $item.title, $item.currency, [double]$item.currentPrice, [double]$item.oldPrice)).ToLowerInvariant()
    if ($seen.ContainsKey($key)) {
        $dupes += $item.title
    }
    else {
        $seen[$key] = $true
    }
}

[pscustomobject]@{
    totalVisible = $facets.total
    marketplaces = $facets.marketplaces.Count
    categories = $facets.categories.Count
    defectSearchTotal = $defect.total
    firstPageReturned = $firstPage.items.Count
    firstPageDuplicateKeys = $dupes.Count
} | ConvertTo-Json -Depth 8

if ($defect.total -gt 0) {
    throw "Bad/defect listings are still visible in API search."
}
if ($dupes.Count -gt 0) {
    throw "Duplicate clone listings are still visible on the first page."
}

Write-Host "Stage 55 cleanup/check completed."
