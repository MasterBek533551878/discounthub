param(
  [Parameter(Mandatory=$true)]
  [string]$Path
)

if (!(Test-Path $Path)) {
  throw "File not found: $Path"
}

$bytes = [System.IO.File]::ReadAllBytes((Resolve-Path $Path))
$base64 = [Convert]::ToBase64String($bytes)

Write-Host "Copy the value below into Codemagic environment variable APP_STORE_CONNECT_PRIVATE_KEY_BASE64:"
Write-Host ""
Write-Output $base64
