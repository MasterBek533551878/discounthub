Param(
    [int[]]$Ports = @(8000, 9000)
)

$ErrorActionPreference = "Continue"

foreach ($Port in $Ports) {
    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $connections) {
        Write-Host "No process is listening on port $Port." -ForegroundColor DarkGray
        continue
    }

    $processIds = $connections | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($ProcessId in $processIds) {
        try {
            $process = Get-Process -Id $ProcessId -ErrorAction Stop
            Write-Host "Stopping port $Port -> PID $ProcessId ($($process.ProcessName))" -ForegroundColor Yellow
            Stop-Process -Id $ProcessId -Force
        } catch {
            Write-Host "Could not stop PID $ProcessId on port $Port: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}
