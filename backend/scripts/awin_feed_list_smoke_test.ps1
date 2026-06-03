param(
  [string]$EnvPath = "$PSScriptRoot\..\.env",
  [int]$PreviewLines = 5
)

$ErrorActionPreference = 'Stop'

function Get-EnvValue([string]$Name) {
  $value = [Environment]::GetEnvironmentVariable($Name)
  if ($value) { return $value }
  if (Test-Path $EnvPath) {
    $line = Get-Content $EnvPath | Where-Object { $_ -match "^$Name=" } | Select-Object -First 1
    if ($line) { return ($line -replace "^$Name=", '').Trim() }
  }
  return ''
}

function Mask-Text([string]$Text, [string]$Secret) {
  if ([string]::IsNullOrWhiteSpace($Secret)) { return $Text }
  return $Text.Replace($Secret, '***AWIN_KEY***')
}

$publisherId = Get-EnvValue 'AWIN_PUBLISHER_ID'
$key = Get-EnvValue 'AWIN_DATAFEED_API_KEY'
$url = Get-EnvValue 'AWIN_FEED_LIST_URL'
$template = Get-EnvValue 'AWIN_FEED_LIST_ENDPOINT_TEMPLATE'
if (-not $template) { $template = 'https://productdata.awin.com/datafeed/list/apikey/{api_key}' }

if (-not $key) { throw 'AWIN_DATAFEED_API_KEY is missing. Run scripts/awin_write_env.ps1 first.' }
if (-not $url) {
  $url = $template.Replace('{api_key}', [uri]::EscapeDataString($key)).Replace('{publisher_id}', [uri]::EscapeDataString($publisherId))
}

Write-Host 'Fetching Awin Feed List Download...' -ForegroundColor Cyan
try {
  $response = Invoke-WebRequest -Uri $url -Method Get -TimeoutSec 30 -UseBasicParsing
} catch {
  Write-Host 'Awin feed-list request failed.' -ForegroundColor Red
  Write-Host $_.Exception.Message
  exit 1
}

Write-Host "HTTP status: $($response.StatusCode)" -ForegroundColor Green
$content = [string]$response.Content
$lines = @($content -split "`r?`n" | Select-Object -First $PreviewLines)
Write-Host ''
Write-Host 'Preview with secret masked:' -ForegroundColor Cyan
foreach ($line in $lines) {
  Write-Host (Mask-Text $line $key)
}

if ($content.Length -lt 5) {
  Write-Host ''
  Write-Host 'Feed list is empty or almost empty. This is normal while advertisers are still Pending.' -ForegroundColor Yellow
}
