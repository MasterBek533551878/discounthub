param(
  [string]$BaseUrl = "http://127.0.0.1:8000",

  [Parameter(Mandatory = $true)]
  [string]$AdminToken,

  [string]$PayloadPath = ""
)

$ErrorActionPreference = "Stop"

$backendRoot = Split-Path -Parent $PSScriptRoot

if ([string]::IsNullOrWhiteSpace($PayloadPath)) {
  $PayloadPath = Join-Path $backendRoot "examples\partner_offer_shakespeare_ai_payload.json"
}

$PayloadPath = (Resolve-Path $PayloadPath).Path

Get-Content -Raw -Encoding UTF8 $PayloadPath |
  ConvertFrom-Json |
  Out-Null

$endpoint = "$($BaseUrl.TrimEnd('/'))/admin/partner-offers"

curl.exe --fail-with-body --silent --show-error `
  -X POST $endpoint `
  -H "X-Admin-Token: $AdminToken" `
  -H "Content-Type: application/json; charset=utf-8" `
  --data-binary "@$PayloadPath"

if ($LASTEXITCODE -ne 0) {
  throw "ShakespeareAI partner offer upsert failed with exit code $LASTEXITCODE."
}