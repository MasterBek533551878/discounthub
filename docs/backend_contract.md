# DiscountHub Backend Contract

DiscountHub is not a marketplace. The backend stores and returns deal metadata collected from official APIs, affiliate feeds, or approved partner feeds. The app opens the original marketplace through `affiliateUrl` or `productUrl`; the backend records the outbound click through `/deals/{id}/click`.

## Local base URL

```text
http://127.0.0.1:8000
```

## Production base URL

Use the deployed backend domain. The Flutter app can receive it at build time:

```powershell
flutter build apk --release --dart-define=DISCOUNTHUB_API_BASE_URL=https://YOUR_BACKEND_DOMAIN
```

## Public endpoints

### GET /health

Returns backend health, app version, storage count, provider/scheduler status where available.

### GET /deals

Returns a paginated list of deals.

Query parameters:

| Name | Example | Meaning |
|---|---|---|
| q | headphones | Search text |
| platform | eBay US | Marketplace/platform |
| category | Electronics | Normalized category |
| ships_to | US | Country code for delivery filtering |
| min_discount | 30 | Minimum discount percent |
| max_price | 100.00 | Maximum current price in requested currency |
| min_rating | 4.0 | Minimum product rating |
| free_shipping | true | Only free shipping deals |
| verified | true | Only verified deals |
| sort | newest | score_desc, discount_desc, price_asc, price_desc, rating_desc, newest |
| currency | USD | Target display currency |
| page | 1 | Page number |
| page_size | 30 | Items per page |

Response shape:

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "pageSize": 30,
  "hasNextPage": false
}
```

### GET /deals/{id}

Returns one deal by ID.

### GET /deals/{id}/click

Records a click event and redirects to the preferred outbound URL:

1. `affiliateUrl` when present;
2. `productUrl` fallback.

### GET /clicks/summary

Returns a small aggregated click summary for diagnostics.

### GET /categories

Returns available category names from stored deals.

### GET /marketplaces

Returns available marketplace/platform names from stored deals.

### GET /settings/rates

Returns temporary currency conversion rates used by the backend.

### GET /storage/status

Returns local storage status.

### GET /security/status

Returns environment/security status for deployment checks.

## Deal object

```json
{
  "id": "ebay_browse_headphones_123",
  "title": "Wireless Headphones",
  "description": "Marketplace-provided product description.",
  "imageUrl": "https://...",
  "platform": "eBay US",
  "category": "Electronics",
  "oldPrice": 129.99,
  "currentPrice": 79.99,
  "currency": "USD",
  "productUrl": "https://marketplace.example/product",
  "affiliateUrl": "https://affiliate.example/product",
  "rating": 4.7,
  "reviewCount": 2841,
  "freeShipping": true,
  "verified": true,
  "shipsTo": ["US", "GB"],
  "hotDeal": true,
  "lowestPrice": false,
  "dealScore": 86,
  "discountPercent": 38,
  "updatedAt": "2026-05-10T00:00:00+00:00",
  "expiresAt": null
}
```

## Admin endpoints

Admin endpoints are protected with `X-Admin-Token` or local `?token=` testing.

```text
GET    /admin/deals
POST   /admin/deals
POST   /admin/deals/bulk
GET    /admin/deals/export
POST   /admin/deals/import
POST   /admin/deals/import-url
GET    /admin/feed-providers
POST   /admin/feed-providers
POST   /admin/feed-providers/{provider_id}/sync
POST   /admin/feed-providers/sync-all
GET    /admin/feed-providers/sync-runs
DELETE /admin/feed-providers/sync-runs
GET    /admin/feed-providers/scheduler/status
POST   /admin/feed-providers/scheduler/start
POST   /admin/feed-providers/scheduler/stop
POST   /admin/feed-providers/scheduler/run-once
```

## Important rules

1. Do not scrape marketplaces without permission.
2. Use official APIs, affiliate APIs, product feeds, or partner-provided feeds.
3. Keep `productUrl` and `affiliateUrl` separate.
4. Always route outbound taps through `/deals/{id}/click` so clicks can be counted.
5. In production, use HTTPS backend URLs and keep admin panel/docs disabled unless explicitly needed.


## Stage 53: Server-side facets and monetization mode

### `GET /deals/facets`

Returns the filter dictionary that the Flutter app should use when it renders marketplace/category/country/currency filters for a large catalog.

Supported query params mirror `GET /deals`: `q`, `platform`, `category`, `ships_to`, `currency`, `min_discount`, `min_rating`, `max_price`, `free_shipping`, `verified`, `monetization_mode`.

Response shape uses camelCase aliases:

```json
{
  "total": 1096,
  "marketplaces": [{ "id": "eBay US", "name": "eBay US", "count": 626 }],
  "categories": [{ "id": "Electronics", "name": "Electronics", "count": 414 }],
  "shippingCountries": [{ "id": "US", "name": "US", "count": 626 }],
  "currencies": [{ "id": "USD", "name": "USD", "count": 626 }],
  "monetizationModes": [{ "id": "direct", "name": "direct", "count": 1096 }],
  "priceRange": { "min": 9.99, "max": 999.99, "currency": "USD" },
  "discountRange": { "min": 15, "max": 80 },
  "generatedAt": "2026-05-26T00:00:00Z"
}
```

### `monetizationMode`

Deals and feed providers now support:

- `direct` — regular store/marketplace link, no commission yet.
- `affiliate` — affiliate/tracking link.
- `pending_affiliate` — traffic collection while waiting for partner approval.

Existing deals are migrated safely. If an old `affiliate_url` equals `product_url`, the deal is treated as `direct`.
