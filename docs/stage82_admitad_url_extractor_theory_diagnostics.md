# Stage 82 Admitad URL extractor theory diagnostics

Dry-run diagnostics only. It does not import, delete, or update data.

Purpose:
- Test whether the old AliExpress-only extractor misses raw Admitad feed URLs.
- Test whether the uploaded broader extractor idea would extract more targets.
- Detect Alibaba `offer.alibaba.com/cps?...productId=...` links that require a different solution than `alibaba.com/product-detail/...` extraction.
- Count whether Alibaba has `price`/`sale_price` discounts.

Run:

```powershell
.\scripts\stage82_admitad_url_extractor_theory_diagnostics.ps1 `
  -ProviderIds "admitad_20881_alibaba_ww_v1","admitad_6115_aliexpress_ww_v1" `
  -MaxRows 500 `
  -TimeoutSeconds 30
```
