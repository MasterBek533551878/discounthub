param(
  [string]$BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

Write-Host "DiscountHub production security/config check" -ForegroundColor Cyan
Write-Host "Base URL: $BaseUrl"
Write-Host ""

try {
  $security = Invoke-RestMethod -Uri "$BaseUrl/security/status" -TimeoutSec 20
  Write-Host "[OK] Security status endpoint reachable" -ForegroundColor Green
} catch {
  Write-Host "[FAIL] Security status endpoint" -ForegroundColor Red
  Write-Host "       $($_.Exception.Message)" -ForegroundColor Yellow
  exit 1
}

Write-Host "Environment:              $($security.environment)"
Write-Host "Production:               $($security.production)"
Write-Host "Safety enforced:          $($security.enforceProductionSafety)"
Write-Host "Admin token configured:   $($security.adminTokenConfigured)"
Write-Host "Uses dev admin token:     $($security.adminTokenIsDevDefault)"
Write-Host "Admin panel enabled:      $($security.adminPanelEnabled)"
Write-Host "Docs enabled:             $($security.docsEnabled)"
Write-Host "OpenAPI enabled:          $($security.openapiEnabled)"
Write-Host "CORS origins:             $($security.corsOrigins -join ', ')"
Write-Host "Status:                   $($security.status)"

if ($security.warnings -and $security.warnings.Count -gt 0) {
  Write-Host ""
  Write-Host "Warnings:" -ForegroundColor Yellow
  foreach ($warning in $security.warnings) {
    Write-Host "- $warning" -ForegroundColor Yellow
  }
}

if ($security.production -and $security.status -ne "ok") {
  Write-Host ""
  Write-Host "Production security check failed. Fix .env before deploy." -ForegroundColor Red
  exit 1
}

Write-Host ""
Write-Host "Security/config check completed." -ForegroundColor Green
