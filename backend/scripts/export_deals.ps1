$ErrorActionPreference = "Stop"

$BaseUrl = $env:DISCOUNTHUB_API_URL
if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
  $BaseUrl = "http://127.0.0.1:8000"
}

$Token = $env:DISCOUNTHUB_ADMIN_TOKEN
if ([string]::IsNullOrWhiteSpace($Token)) {
  $Token = "dev-local-admin-token"
}

$OutDir = Join-Path $PSScriptRoot "..\exports"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$OutFile = Join-Path $OutDir "discounthub-deals-$Stamp.json"

Invoke-RestMethod `
  -Method GET `
  -Uri "$BaseUrl/admin/deals/export" `
  -Headers @{ "X-Admin-Token" = $Token } |
  ConvertTo-Json -Depth 12 |
  Set-Content -Path $OutFile -Encoding UTF8

Write-Host "Export saved to: $OutFile"
