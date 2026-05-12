# DiscountHub local dev automation

Stage 26 adds helper scripts so you do not need to manually manage multiple PowerShell windows every time.

## Start everything for local development

From the backend folder:

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend
.\.venv\Scripts\Activate.ps1
.\scripts\run_all_dev.ps1
```

This opens separate PowerShell windows for:

- demo feed server on `http://127.0.0.1:9000`
- FastAPI backend on `http://127.0.0.1:8000`

Then open:

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/admin-panel
```

## Check that everything works

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend
.\.venv\Scripts\Activate.ps1
.\scripts\dev_health_check.ps1
```

The health check tests:

- backend health
- SQLite storage
- deals API
- demo feed file
- generic adapter demo feed
- Google Merchant-style demo feed
- Awin-style demo feed
- admin feed providers
- scheduler status

## Sync all demo adapter feeds

Run this after backend `8000` and feed server `9000` are both running:

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend
.\.venv\Scripts\Activate.ps1
.\scripts\sync_all_demo_sources.ps1
```

## Stop local dev ports

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend
.\.venv\Scripts\Activate.ps1
.\scripts\stop_dev_ports.ps1
```

This stops processes listening on ports `8000` and `9000`.

## Real production idea

The demo feed server is only for local testing. In production, feed provider URLs should be real official HTTPS URLs from affiliate networks or marketplace APIs. The backend scheduler will sync them automatically.
