# Stage 88 — Awin Offers / Promotions import

This stage fills the Stage 87 `Promos` / `Акции` tab with real Awin My Offers data.

## What it imports

- Awin voucher codes -> `type=coupon`
- Awin store promotions -> `type=sale`
- urgent/limited-time wording -> `type=flash_sale`

Concrete product discounts still belong in `/deals`; this importer only handles store-level offers and voucher codes.

## Requirements

Backend `.env` must contain:

```env
AWIN_PUBLISHER_ID=...
AWIN_DATAFEED_API_KEY=...
# Optional if your Awin account uses a separate Publisher API token:
AWIN_API_ACCESS_TOKEN=...
```

If `AWIN_API_ACCESS_TOKEN` is empty, the backend falls back to `AWIN_DATAFEED_API_KEY`.

## Local sync

Start backend, then run from project root:

```powershell
.\scripts\stage88_sync_awin_promotions.ps1
```

If Awin returns 401/403, add the correct Awin API token to `AWIN_API_ACCESS_TOKEN` in `backend/.env`, restart backend, and rerun the script.
