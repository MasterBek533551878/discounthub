# DiscountHub Stage 78 — Admitad AliExpress WW quarantine

## What was proven

For campaign `6115` / provider `admitad_6115_aliexpress_ww_v1`:

- direct product URL opens the exact AliExpress product page;
- stored Admitad `affiliateUrl` from the feed opens the AliExpress homepage;
- official Admitad Deeplink Generator returns the same style of URL and also opens the homepage;
- `ulp` and localized AliExpress domains were tested, but they still opened the homepage.

This means the current issue is not a DiscountHub backend deeplink construction bug. It is a campaign/feed/deeplink behavior issue for AliExpress WW through Admitad in our current account/region flow.

## What this patch does

- Keeps the general Admitad integration for future stores.
- Excludes Admitad campaign `6115` (AliExpress WW) from automatic active product-feed registration by default.
- Makes the old Stage 64 AliExpress WW sync script refuse to run unless `-ForceKnownBrokenAliExpressWW` is explicitly passed.
- Adds a quarantine helper script to disable `admitad_6115_aliexpress_ww_v1` and delete only its imported deals from production DB.

## What is not affected

- eBay providers are not touched.
- Awin AliExpress PL is not touched.
- Future Admitad stores are not blocked.

## Use

Dry run:

```powershell
.\scripts\stage78_quarantine_admitad_aliexpress_ww.ps1
```

Apply:

```powershell
.\scripts\stage78_quarantine_admitad_aliexpress_ww.ps1 -Apply
```

## Future Admitad stores

When a new Admitad advertiser is approved, run registration and then verify a few clicks. If the affiliate click opens the exact product page, keep it enabled. If it opens the store homepage, quarantine only that campaign/provider.
