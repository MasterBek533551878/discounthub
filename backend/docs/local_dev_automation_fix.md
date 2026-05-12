# Local dev automation fix

`run_all_dev.ps1` now starts two separate PowerShell windows using encoded commands.
This avoids quoting problems with paths and titles such as `DiscountHub backend :8000`.

Use:

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend
.\.venv\Scripts\Activate.ps1
.\scripts\run_all_dev.ps1
```

Then check:

```powershell
.\scripts\dev_health_check.ps1
```
