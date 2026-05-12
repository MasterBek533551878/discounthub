$ErrorActionPreference = "Stop"

$backendRoot = Split-Path -Parent $PSScriptRoot
$payloadPath = Join-Path $backendRoot "examples\admin_deal_payload.json"
$body = Get-Content $payloadPath -Raw

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/admin/deals" `
  -Headers @{ "X-Admin-Token" = "dev-local-admin-token" } `
  -ContentType "application/json" `
  -Body $body
