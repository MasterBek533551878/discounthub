# Stage 47 — Universal affiliate product feeds

DiscountHub can now ingest affiliate product feeds in JSON, CSV and TSV format.

This stage is designed for adding global affiliate networks and online shops without changing the Flutter app each time.

Supported adapters:

- `csv_products` — universal CSV/TSV product feed
- `generic_products` — generic JSON product feed
- `awin_products` — Awin-like product feeds
- `admitad_products` — Admitad-like product feeds
- `rakuten_products` — Rakuten-like product feeds
- `cj_products` — CJ-like product feeds
- `impact_products` — Impact-like product feeds

The app still shows one global deal catalog. A provider's country or network does not hide products by user country. Country is only used for currency and shipping badges when shipping countries are known.

## Local CSV test

Terminal 1:

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal 2:

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend
.\scripts\start_provider_feed_server.ps1
```

Terminal 3:

```powershell
cd C:\Users\Victus\Desktop\discounthub
.\backend\scripts\stage47_test_affiliate_csv_feed.ps1
```

## Real feed usage

When an affiliate network gives you a product feed URL, register it like this:

```powershell
cd C:\Users\Victus\Desktop\discounthub
.\backend\scripts\stage47_add_affiliate_feed_provider.ps1 `
  -ProviderId "awin_fashion_global" `
  -Name "Awin Fashion Global" `
  -FeedUrl "https://your-real-feed-url.csv" `
  -Adapter "awin_products"

.\backend\scripts\stage47_sync_affiliate_feed_provider.ps1 -ProviderId "awin_fashion_global"
```

Use `replaceOnSync` only when the provider feed is the complete source of truth for that provider. Otherwise leave it off so eBay and other providers are not removed.
