param(
  [string]$EnvPath = "$PSScriptRoot\..\.env",
  [string]$OAuthUrl = '',
  [string]$Scope = ''
)

$ErrorActionPreference = 'Stop'

function Get-EnvValue([string]$Name, [string]$Default = '') {
  $value = [Environment]::GetEnvironmentVariable($Name)
  if ($value) { return $value }
  if (Test-Path $EnvPath) {
    $line = Get-Content $EnvPath | Where-Object { $_ -match "^$Name=" } | Select-Object -First 1
    if ($line) { return ($line -replace "^$Name=", '').Trim() }
  }
  return $Default
}

$clientId = Get-EnvValue 'EBAY_CLIENT_ID'
$clientSecret = Get-EnvValue 'EBAY_CLIENT_SECRET'
if (-not $OAuthUrl) { $OAuthUrl = Get-EnvValue 'EBAY_OAUTH_URL' 'https://api.ebay.com/identity/v1/oauth2/token' }
if (-not $Scope) { $Scope = Get-EnvValue 'EBAY_SCOPE' 'https://api.ebay.com/oauth/api_scope' }

Write-Host 'DiscountHub eBay OAuth smoke test' -ForegroundColor Cyan
Write-Host "OAuth URL: $OAuthUrl"
Write-Host "Scope:     $Scope"

if (-not $clientId -or -not $clientSecret) {
  throw 'EBAY_CLIENT_ID and EBAY_CLIENT_SECRET are required. Use ebay_write_env.ps1 first.'
}

$pair = "${clientId}:${clientSecret}"
$bytes = [System.Text.Encoding]::ASCII.GetBytes($pair)
$basic = [Convert]::ToBase64String($bytes)

$headers = @{
  Authorization = "Basic $basic"
  'Content-Type' = 'application/x-www-form-urlencoded'
  Accept = 'application/json'
}
$body = "grant_type=client_credentials&scope=$([System.Uri]::EscapeDataString($Scope))"

try {
  $response = Invoke-RestMethod -Uri $OAuthUrl -Method Post -Headers $headers -Body $body -TimeoutSec 30
} catch {
  Write-Host 'FAILED' -ForegroundColor Red
  Write-Host $_.Exception.Message
  if ($_.Exception.Response) {
    try {
      $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
      $bodyText = $reader.ReadToEnd()
      Write-Host $bodyText
    } catch {}
  }
  exit 1
}

$token = [string]$response.access_token
Write-Host 'OK: eBay OAuth token received.' -ForegroundColor Green
Write-Host "Token length: $($token.Length)"
Write-Host "Expires in:   $($response.expires_in) seconds"
Write-Host 'Token is not printed for safety.'
