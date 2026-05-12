# Docker is not installed

If `docker` is not recognized in PowerShell, Docker Desktop is not installed or not available in PATH.

For local testing without Docker, use:

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend
.\.venv\Scripts\Activate.ps1
.\scripts\production_start_local.ps1
```

Then check:

```powershell
.\scripts\production_health_check.ps1 -BaseUrl http://127.0.0.1:8000 -AdminToken dev-local-admin-token
```

For real Docker testing, install Docker Desktop, restart PowerShell, then run:

```powershell
.\scripts\docker_build.ps1
.\scripts\docker_run_local.ps1
```
