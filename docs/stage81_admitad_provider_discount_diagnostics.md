# DiscountHub Stage 81 — Admitad provider discount diagnostics

Dry-run diagnostics for a single Admitad product-feed provider, defaulting to `admitad_20881_alibaba_ww_v1`.

This script does **not** import, delete, or modify production data. It reads the registered provider from the server SQLite database, downloads the feed, scans rows, and reports how many rows would pass DiscountHub discount rules.

## Usage

```powershell
cd C:\Users\Victus\Desktop\discounthub

Expand-Archive -Path C:\Users\Victus\Downloads\discounthub_stage81_admitad_provider_discount_diagnostics_patch.zip -DestinationPath . -Force

.\scripts\stage81_admitad_provider_discount_diagnostics.ps1 `
  -ProviderId "admitad_20881_alibaba_ww_v1" `
  -MaxRows 25000 `
  -TimeoutSeconds 30
```

## Result interpretation

- `passed >= 10% > 0`: provider has rows that can pass current production rules.
- `passed >= 1% > 0` but `passed >= 10% = 0`: provider has small discounts, but not enough for current app rules.
- `no_discount_pair` high: feed has products but no clear old/current price pair.
- `out_of_stock` high: feed returns unavailable products.
- `missing_image/link/price` high: feed is not suitable for product cards.

## Safety

The script is dry-run only. It does not call `/admin/feed-providers/{id}/sync`.
