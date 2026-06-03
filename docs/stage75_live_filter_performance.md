# Stage 75 — live filter performance

This stage reduces the delay when the Flutter app opens or applies filters after large Awin/eBay imports.

Changes:
- SQLite now stores materialized helper columns on `deals`: `public_platform`, `discount_percent`, `current_price_usd`, and `search_text`.
- New indexes speed up marketplace/category/price/discount filters.
- Backend uses short in-memory caching for `/deals/facets` so opening filters does not repeat the same expensive aggregation every time.
- Flutter no longer refreshes `/deals/facets` on every page-one search/filter request if it already has fresh backend facets.
- SQLite connection pragmas use WAL, temp memory, larger cache, and a busy timeout to reduce stalls during local syncs.

Run after applying the patch:

```powershell
.\scripts\stage75_optimize_filters_and_check.ps1
```

Restart the backend after applying the patch so FastAPI uses the new repository and service code.
