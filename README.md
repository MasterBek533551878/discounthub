# DiscountHub

DiscountHub is a Flutter + FastAPI discount aggregator. It does not sell products directly: the app shows deal metadata from official marketplace APIs and affiliate/product feeds, then opens the original marketplace through a tracked affiliate/deep link.

Current MVP direction:

- no required registration;
- no in-app cart or checkout;
- real deals from feed providers, starting with eBay Browse API;
- local favorites and settings in the Flutter app;
- backend storage, scheduled feed sync, admin endpoints, and click tracking.

## Current architecture

```text
Flutter app
  -> GET /deals
  -> GET /deals/{id}
  -> GET /deals/{id}/click
  -> opens marketplace / affiliate URL

FastAPI backend
  -> SQLite storage
  -> feed provider registry
  -> feed scheduler
  -> eBay Browse API adapter
  -> CSV / affiliate feed adapters
  -> admin API / local admin panel
```

## Main folders

```text
lib/                         Flutter application
backend/app/                 FastAPI backend
backend/config/              Feed provider configuration
backend/scripts/             PowerShell helper scripts
backend/docs/                Backend operation notes
assets/brand/logo.png        App logo asset
```

## Local backend run

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod "http://127.0.0.1:8000/deals?page_size=5&sort=newest"
```

## Flutter local run

For a real Android phone over USB, keep the backend on `127.0.0.1:8000` through adb reverse:

```powershell
adb reverse tcp:8000 tcp:8000
flutter run
```

For a production/staging API URL, build with a Dart define:

```powershell
flutter build apk --release --dart-define=DISCOUNTHUB_API_BASE_URL=https://YOUR_BACKEND_DOMAIN
```

## MVP freeze cleanup

Stage 48 adds cleanup tools for the current near-final MVP state:

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend
.\.venv\Scripts\Activate.ps1
python .\scripts\stage48_mvp_cleanup.py
```

The cleanup script backs up the SQLite database, removes known sample providers/deals, disables the broken temporary Awin provider, and normalizes raw eBay category names into a smaller product category set.

## Before production

Do not ship or commit local runtime artifacts:

- `backend/.env`
- `backend/.venv/`
- `backend/data/*.sqlite3`
- `backend/exports/`
- `lib.zip`
- generated ZIP archives

Use `.env.production.example` as a template, set a real `ADMIN_API_TOKEN`, real CORS origins, production backend URL in the app build, and an eBay EPN `EBAY_CAMPAIGN_ID` when affiliate monetization is ready.
