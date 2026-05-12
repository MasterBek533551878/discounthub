$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Split-Path -Parent $ScriptDir
$BackendScript = Join-Path $ScriptDir "run_backend_auto.ps1"
$FeedScript = Join-Path $ScriptDir "start_provider_feed_server.ps1"

function Assert-FileExists {
  param(
    [Parameter(Mandatory = $true)]
    [string] $Path
  )

  if (-not (Test-Path -LiteralPath $Path)) {
    throw "Required file not found: $Path"
  }
}

function Start-DiscountHubWindow {
  param(
    [Parameter(Mandatory = $true)]
    [string] $Title,

    [Parameter(Mandatory = $true)]
    [string] $ScriptPath
  )

  Assert-FileExists -Path $ScriptPath

  $Command = @"
`$ErrorActionPreference = 'Stop'
`$host.UI.RawUI.WindowTitle = '$Title'
Set-Location -LiteralPath '$BackendDir'
& '$ScriptPath'
"@

  $EncodedCommand = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($Command))

  Start-Process powershell.exe -WorkingDirectory $BackendDir -ArgumentList @(
    '-NoExit',
    '-NoProfile',
    '-ExecutionPolicy',
    'Bypass',
    '-EncodedCommand',
    $EncodedCommand
  )
}

Write-Host "Starting DiscountHub local dev environment..." -ForegroundColor Cyan
Write-Host "Backend directory: $BackendDir"

Start-DiscountHubWindow -Title "DiscountHub feed server :9000" -ScriptPath $FeedScript
Start-Sleep -Seconds 1
Start-DiscountHubWindow -Title "DiscountHub backend :8000" -ScriptPath $BackendScript

Write-Host ""
Write-Host "Started two PowerShell windows:" -ForegroundColor Green
Write-Host "  - Feed server: http://127.0.0.1:9000/provider_feed.json"
Write-Host "  - Backend API:  http://127.0.0.1:8000/health"
Write-Host ""
Write-Host "After a few seconds, run:" -ForegroundColor Yellow
Write-Host "  .\scripts\dev_health_check.ps1"
