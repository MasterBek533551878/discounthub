param(
  [Parameter(Mandatory=$true)]
  [string]$Path,

  [switch]$Replace
)

$ErrorActionPreference = "Stop"

$BaseUrl = $env:DISCOUNTHUB_API_URL
if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
  $BaseUrl = "http://127.0.0.1:8000"
}

$Token = $env:DISCOUNTHUB_ADMIN_TOKEN
if ([string]::IsNullOrWhiteSpace($Token)) {
  $Token = "dev-local-admin-token"
}

$Json = Get-Content -Path $Path -Raw -Encoding UTF8 | ConvertFrom-Json

if ($Json.items) {
  $Items = $Json.items
} else {
  $Items = $Json
}

$Body = @{
  replace = [bool]$Replace
  items = $Items
} | ConvertTo-Json -Depth 12

Invoke-RestMethod `
  -Method POST `
  -Uri "$BaseUrl/admin/deals/import" `
  -Headers @{ "X-Admin-Token" = $Token; "Content-Type" = "application/json" } `
  -Body $Body
