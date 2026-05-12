# eBay credentials setup for DiscountHub

DiscountHub's `ebay_browse_api` adapter uses the eBay Browse API.

## What you need

1. eBay Developer Program account.
2. Production application keys:
   - Client ID
   - Client Secret
3. Optional eBay Partner Network campaign ID for affiliate links.

## Why these values are needed

The Browse API `item_summary/search` call requires an application access token created with the OAuth client credentials flow and the scope:

```text
https://api.ebay.com/oauth/api_scope
```

For affiliate attribution, eBay expects affiliate values in the `X-EBAY-C-ENDUSERCTX` header. When configured, the Browse API can return `itemAffiliateWebUrl`, which DiscountHub stores as the affiliate URL.

## Local setup

From `backend/`:

```powershell
.\.venv\Scripts\Activate.ps1
.\scripts\ebay_write_env.ps1 `
  -ClientId "YOUR_CLIENT_ID" `
  -ClientSecret "YOUR_CLIENT_SECRET" `
  -CampaignId "YOUR_EPN_CAMPAIGN_ID" `
  -ReferenceId "discounthub" `
  -MarketplaceId "EBAY_US"
```

Restart backend after writing `.env`.

## Smoke tests

```powershell
.\scripts\ebay_env_check.ps1
.\scripts\ebay_oauth_smoke_test.ps1
.\scripts\ebay_browse_smoke_test.ps1 -Query "wireless headphones" -Limit 5
```

## Enable the provider

The eBay provider is intentionally disabled until credentials are ready.

```powershell
.\scripts\ebay_enable_provider_in_config.ps1 -Id "ebay_browse_headphones" -Enabled $true
```

Then restart backend, or register config again:

```powershell
.\scripts\provider_sync_from_config.ps1
.\scripts\sync_ebay_browse_provider.ps1 -ProviderId ebay_browse_headphones
```

## Production notes

- Do not commit `.env`.
- Use a real `ADMIN_API_TOKEN` in production.
- Keep `/admin-panel` and `/docs` disabled in strict production.
- Use official API/feed access only. Do not scrape eBay pages.
