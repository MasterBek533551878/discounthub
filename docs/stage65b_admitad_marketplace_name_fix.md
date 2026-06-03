# Stage 65b — Admitad marketplace name final fix

Fixes two missed places from Stage 65:

- Stage 57 now actually appends `discounthub_platform_name=<program name>` to Admitad feed URLs.
- `admitad_products` adapter now reads `_discounthub_platform_name` before falling back to CSV merchant columns.
- Stage 64 sample query now uses the real API parameter `platform=AliExpress WW` instead of the ignored `marketplace=` parameter.

After applying this patch, restart the backend and re-run Stage 64. Existing Admitad rows should be upserted from `Admitad Merchant` to `AliExpress WW`.
