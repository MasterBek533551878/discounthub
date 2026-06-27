param(
  [string]$BaseUrl = "http://127.0.0.1:8000",
  [string]$AdminToken = "dev-local-admin-token",
  [string]$PayloadPath = ""
)

$ErrorActionPreference = "Stop"

$backendRoot = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($PayloadPath)) {
  $PayloadPath = Join-Path $backendRoot "examples\partner_offer_preflight_payload.json"
}

curl.exe -X POST "$BaseUrl/admin/partner-offers" `
  -H "X-Admin-Token: $AdminToken" `
  -H "Content-Type: application/json; charset=utf-8" `
  --data-binary "@$PayloadPath"
