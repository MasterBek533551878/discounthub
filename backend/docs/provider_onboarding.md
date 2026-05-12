# DiscountHub provider onboarding

This document describes the production flow for adding real marketplace / affiliate sources without manually creating products.

## Goal

Products must come from official sources only:

- affiliate product feeds;
- marketplace APIs;
- partner JSON/XML exports;
- merchant feeds that the provider explicitly allows you to use.

Do not scrape marketplace websites directly unless the provider explicitly permits it in writing.

## Recommended onboarding flow

1. Apply to a marketplace or affiliate network.
2. Get an official product feed or API endpoint.
3. Confirm that the feed includes product title, image, price, old price or discount, product URL, affiliate URL, currency, category, availability and shipping information.
4. Choose the closest DiscountHub adapter.
5. Add the provider to `backend/config/feed_providers.json` or production env/config.
6. Run one manual sync.
7. Check `/admin-panel`, `/storage/status`, `/deals` and the mobile app.
8. Enable automatic scheduler.

## Adapter selection

| Adapter | Use when |
|---|---|
| `discounthub_json` | The feed is already in DiscountHub format. |
| `generic_products` | The feed has common fields like `name`, `price`, `sale_price`, `image`, `url`. |
| `google_merchant` | The feed looks like Google Merchant Center product JSON. |
| `awin_products` | The feed looks like an Awin-style product feed. |
| `auto` | Development/testing only. The backend tries to detect the format. |

## Required provider fields

Each provider should have:

```json
{
  "id": "provider_unique_id",
  "name": "Provider display name",
  "url": "https://official-provider-feed.example.com/products.json",
  "adapter": "generic_products",
  "enabled": true,
  "replaceOnSync": false
}
```

## Production rules

- Use a real `ADMIN_API_TOKEN`.
- Disable `/admin-panel` in production unless it is protected behind private access.
- Disable docs/openapi in public production.
- Do not store secret affiliate tokens inside committed JSON files.
- If a feed requires credentials, use environment variables or a server-side secret store.
- Keep feed contracts documented per provider.

## Validation checklist

Before enabling a new provider in production:

- [ ] Feed URL is official and allowed by provider terms.
- [ ] Affiliate links are allowed in mobile apps.
- [ ] The feed can be refreshed automatically.
- [ ] Images are licensed/allowed to display.
- [ ] Prices include currency.
- [ ] Old/current price fields are trustworthy.
- [ ] Product URLs open correctly.
- [ ] Shipping region is available or can be inferred.
- [ ] Duplicate IDs are stable.
- [ ] Sync history shows `ok`.
