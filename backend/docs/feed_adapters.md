# DiscountHub feed adapters

DiscountHub should not depend on manual product entry. The normal flow is:

```text
Official / affiliate feed URL
        ↓
Provider adapter normalizes the feed
        ↓
Deals are saved into SQLite
        ↓
Scheduler keeps feeds updated automatically
        ↓
Flutter app reads `/deals`
```

## Supported adapters

| Adapter | Use case |
|---|---|
| `auto` | Backend detects the format from the first item. Good for testing. |
| `discounthub_json` | Native DiscountHub JSON fields: `title`, `oldPrice`, `currentPrice`, `productUrl`, etc. |
| `generic_products` | Common partner feeds with fields like `name`, `sale_price`, `list_price`, `merchant`, `link`. |
| `google_merchant` | Google Merchant-style product feeds with `image_link`, `sale_price`, `price`, `link`, `product_type`. |
| `awin_products` | Awin-like product feeds with `product_name`, `merchant_name`, `deep_link`, `product_price`, `rrp_price`. |

## Provider config

`backend/config/feed_providers.json` now supports the `adapter` field:

```json
{
  "providers": [
    {
      "id": "demo_feed",
      "name": "Demo provider feed",
      "url": "http://127.0.0.1:9000/provider_feed.json",
      "adapter": "discounthub_json",
      "enabled": true,
      "replaceOnSync": false
    }
  ]
}
```

## Local test

Keep the demo feed server running:

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend
.\.venv\Scripts\Activate.ps1
.\scripts\start_provider_feed_server.ps1
```

Then add and sync adapter demo providers:

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend
.\.venv\Scripts\Activate.ps1
.\scripts\add_generic_feed_provider.ps1
.\scripts\add_google_merchant_feed_provider.ps1
.\scripts\add_awin_feed_provider.ps1
.\scripts\sync_adapter_demo_providers.ps1
```

The deal count should increase by up to 3, depending on whether those demo IDs already exist.

## Production note

For real affiliate/marketplace integrations, create one provider per official feed/API source and choose the closest adapter. If a partner uses a unique format, add a new adapter in `backend/app/services/feed_adapters.py` rather than changing the app UI.
