# Stage 64 — Admitad safe product-feed sync

This stage keeps Admitad product feed imports bounded and production-safe.

Changes:
- `admitad_products` provider sync now streams CSV feeds instead of loading the full feed into memory.
- Admitad sync has default safety limits: max 2,000 imported rows, max 25,000 scanned rows, minimum 10% discount.
- Local URL controls are supported through `discounthub_max_items`, `discounthub_max_scan_rows`, and `discounthub_min_discount_percent` in the feed URL query or fragment. These local options are removed before the remote feed URL is requested.
- Existing Admitad providers can be re-registered safely with `stage57_register_active_admitad_product_feeds.ps1`.
- Added `stage64_check_admitad_aliexpress_sync.ps1` to re-register, sync, show logs, and verify facets.

Recommended local command:

```powershell
.\scripts\stage64_check_admitad_aliexpress_sync.ps1 -MaxItemsPerFeed 2000 -MaxScanRows 25000 -MinDiscountPercent 10 -TimeoutSeconds 300
```
