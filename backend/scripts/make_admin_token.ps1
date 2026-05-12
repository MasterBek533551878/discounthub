# Generates a strong random admin token for DiscountHub production.
# Compatible with older Windows PowerShell/.NET versions where
# [System.Security.Cryptography.RandomNumberGenerator]::Fill() is unavailable.

param(
  [int]$Bytes = 32
)

if ($Bytes -lt 32) {
  Write-Error "Token should be at least 32 random bytes. Use -Bytes 32 or higher."
  exit 1
}

$buffer = New-Object byte[] $Bytes
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
try {
  $rng.GetBytes($buffer)
} finally {
  if ($null -ne $rng) {
    $rng.Dispose()
  }
}

$token = [Convert]::ToBase64String($buffer)
$token = $token.TrimEnd('=').Replace('+', '-').Replace('/', '_')

Write-Host "Generated ADMIN_API_TOKEN:" -ForegroundColor Green
Write-Host $token
Write-Host ""
Write-Host "Use it in production env as:" -ForegroundColor Yellow
Write-Host "ADMIN_API_TOKEN=$token"
