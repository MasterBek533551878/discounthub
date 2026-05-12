# Stage 48 — MVP cleanup / freeze

Goal: make the current DiscountHub state easier to finish instead of adding more moving parts.

## What changed

- Root README now describes the real product instead of the default Flutter template.
- Backend README now reflects the current FastAPI + SQLite + feed provider architecture.
- `.gitignore` now excludes local secrets, virtualenvs, SQLite databases, exports, logs, and ZIP archives.
- `backend/config/feed_providers.json` now contains only real eBay providers; old disabled demo providers were removed from config.
- Android debug builds still allow local HTTP testing; Android release builds now set `usesCleartextTraffic=false`.
- Flutter API base URL can now be set at build time with `DISCOUNTHUB_API_BASE_URL`.
- Removed hardcoded local LAN fallback `192.168.1.6` from the app.
- Added backend category normalization so raw marketplace category names become a smaller clean set: `Electronics`, `Computers`, `Fashion`, `Gaming`, `Home`, `Other`.
- Added a local cleanup script for the current SQLite database.
- Added a clean ZIP helper script to avoid sending/committing `.env`, `.venv`, SQLite DB, and generated archives.

## Apply patch

```powershell
cd C:\Users\Victus\Desktop\discounthub
Expand-Archive -Path C:\Users\Victus\Downloads\DiscountHub_stage48_mvp_cleanup.zip -DestinationPath . -Force
```

## Run cleanup

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend
.\.venv\Scripts\Activate.ps1
python .\scripts\stage48_mvp_cleanup.py
```

Expected approximate result from the uploaded ZIP database:

```text
Before: 601 deals, 36 providers
After:  598 deals, 30 providers
Categories: Fashion, Electronics, Computers, Home, Gaming
```

The script creates a backup like:

```text
backend/data/discounthub.sqlite3.stage48_backup_YYYYMMDD-HHMMSS
```

## Verify backend

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend
.\.venv\Scripts\Activate.ps1
.\scripts\dev_health_check.ps1
```

Then check categories:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/categories"
Invoke-RestMethod "http://127.0.0.1:8000/deals?page_size=5&sort=newest"
```

## Build app with production API later

```powershell
flutter build apk --release --dart-define=DISCOUNTHUB_API_BASE_URL=https://YOUR_BACKEND_DOMAIN
```

For local USB phone testing:

```powershell
adb reverse tcp:8000 tcp:8000
flutter run
```
