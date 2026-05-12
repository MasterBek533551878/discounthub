# eBay Browse API adapter

Stage 31 adds the first real API adapter for DiscountHub: `ebay_browse_api`.

This adapter does **not** scrape eBay pages. It uses official eBay APIs and converts the Browse API `itemSummaries` response into the unified DiscountHub deal model.

## Provider URL format

Use a special provider URL instead of a normal JSON feed URL:

```text
ebay://browse?q=wireless%20headphones&marketplace_id=EBAY_US&limit=50&sort=price
```

Supported query parameters:

- `q` — keyword search, for example `wireless headphones`.
- `marketplace_id` — eBay marketplace, for example `EBAY_US`.
- `limit` — result count per request.
- `offset` — pagination offset.
- `category_ids` — optional category IDs.
- `filter` — optional eBay Browse API filter expression.
- `sort` — optional eBay sort expression.

## Required environment values

Add these values to `backend/.env` for local real API testing:

```env
EBAY_CLIENT_ID=your-ebay-client-id
EBAY_CLIENT_SECRET=your-ebay-client-secret
EBAY_SCOPE=https://api.ebay.com/oauth/api_scope
EBAY_OAUTH_URL=https://api.ebay.com/identity/v1/oauth2/token
EBAY_API_BASE_URL=https://api.ebay.com
EBAY_DEFAULT_MARKETPLACE_ID=EBAY_US
EBAY_CAMPAIGN_ID=
EBAY_REFERENCE_ID=discounthub
```

`EBAY_CAMPAIGN_ID` is optional during API testing, but should be filled when your eBay Partner Network tracking is ready.

## Add provider

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend
.\.venv\Scripts\Activate.ps1
.\scripts\add_ebay_browse_provider.ps1 -Query "wireless headphones" -Enabled $false
```

The provider is disabled by default so the scheduler will not fail before credentials are configured.

## Check credentials

```powershell
.\scripts\ebay_env_check.ps1
```

## Enable and sync

After credentials are configured, enable the provider from `/admin-panel`, or add it again with `-Enabled $true`, then sync:

```powershell
.\scripts\sync_ebay_browse_provider.ps1 -ProviderId ebay_browse_headphones
```

## What fields are mapped

- `itemId` -> `id`
- `title` -> `title`
- `shortDescription` -> `description`
- `image.imageUrl` -> `imageUrl`
- `price.value` -> `currentPrice`
- `marketingPrice.originalPrice.value` -> `oldPrice`
- `itemWebUrl` -> `productUrl`
- `itemAffiliateWebUrl` -> `affiliateUrl` when eBay returns it
- `shippingOptions.shippingCost.value == 0` -> `freeShipping`

## Notes

The adapter is ready, but real sync requires eBay Developer credentials. Without credentials the backend will return a clear error and keep the app using the existing data.
