# Stage 76 — Admitad deeplinks + stock quality

This patch is backend-only. It does not change Flutter, eBay click routing, or Awin deeplink behavior.

## What changed

1. Admitad AliExpress product feeds now build product deeplinks explicitly:

   `ad.admitad.com/g/<code>/?ulp=<encoded AliExpress item URL>`

   This is scoped to `_normalize_admitad()` in `feed_adapters.py`. If a non-Admitad URL reaches the helper, it is returned unchanged.

2. eBay Browse imports now reject items that explicitly report `OUT_OF_STOCK`, `UNAVAILABLE`, `SOLD_OUT`, `ENDED`, or quantity `0`.

3. Awin and Admitad feed import filters now recognize more availability headers, including `g:availability` / `g_availability`.

## Checks

```powershell
.\scripts\stage76_check_admitad_deeplink_and_stock.ps1
```

## Optional cleanup

Dry-run first:

```powershell
.\scripts\stage76_cleanup_admitad_default_links.ps1
```

Apply after reviewing output:

```powershell
.\scripts\stage76_cleanup_admitad_default_links.ps1 -Apply
```

After cleanup, re-register/sync Admitad providers and check several `/deals/{id}/click` redirects manually.
