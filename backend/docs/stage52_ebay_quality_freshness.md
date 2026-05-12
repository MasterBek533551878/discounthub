# Stage 52 — eBay quality + freshness cleanup

Goal: keep DiscountHub V1 focused on live, real eBay discounts instead of stale listings, repair parts, broken products, accessories-only items, or non-discount catalogue items.

## What this stage does

1. Hardens all eBay provider URLs in both:
   - `backend/config/feed_providers.json`
   - SQLite `feed_providers` table

2. Adds stronger local exclusions to eBay provider URLs:
   - broken / not working / for repair
   - parts only / spares
   - empty box / case only / manual only
   - charger only / cable only / screen protector
   - replacement / Ersatz / mainboard / logic board

3. Cleans the current SQLite `deals` table:
   - removes eBay listings below the selected minimum discount
   - removes stale eBay listings older than the selected freshness window
   - removes placeholder-image rows
   - removes rows with obvious bad keywords

## Recommended local run

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend
.\.venv\Scripts\Activate.ps1
.\scripts\stage52_run_ebay_quality_freshness.ps1 -SyncFirst -TimeoutSeconds 35 -MinDiscount 15 -MaxAgeHours 72
```

The cleanup script creates a SQLite backup by default:

```text
backend/data/discounthub.sqlite3.stage52_backup_YYYYMMDD-HHMMSS
```

## Server/VPS recommendation

On the VPS, run feed sync first, then Stage 52 cleanup after sync. This keeps the app showing only recently confirmed eBay deals.

A simple V1 schedule can be:

```text
hourly: backend scheduler syncs eBay providers
hourly/daily after sync: stage52 cleanup removes stale/bad rows
```

For production we can later turn this into a systemd timer or an internal backend job.
