# Stage 65 — Admitad marketplace name fix

Admitad AliExpress feeds may not include a merchant/shop column in every CSV row, so imported deals used the fallback platform name `Admitad Merchant`.

Changes:
- Stage 57 registration now stores a DiscountHub-only `discounthub_platform_name=<program name>` option in the feed URL fragment.
- Feed import strips this local option before downloading the remote CSV, then attaches `_discounthub_platform_name` to each imported row.
- `admitad_products` adapter uses `_discounthub_platform_name` before falling back to CSV merchant/shop fields.
- Re-running Stage 64 will upsert existing Admitad rows and rename their marketplace from `Admitad Merchant` to `AliExpress WW`.

Recommended command:

```powershell
.\scripts\stage64_check_admitad_aliexpress_sync.ps1 -MaxItemsPerFeed 2000 -MaxScanRows 25000 -MinDiscountPercent 10 -TimeoutSeconds 300
```
