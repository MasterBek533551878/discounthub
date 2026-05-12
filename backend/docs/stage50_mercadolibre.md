# Stage 50 — Mercado Libre data expansion

This stage adds a first non-eBay marketplace source for DiscountHub.

## What it does

- Adds a `mercadolibre_search_api` feed adapter.
- Uses local provider URLs like `mercadolibre://search?site_id=MLM&q=laptop&limit=50`.
- Converts them to the official Mercado Libre public search endpoint: `/sites/{site_id}/search`.
- Adds enabled providers for Mexico, Brazil, and Argentina.
- Does not require an affiliate account, campaign ID, app approval, or API key.

## Supported site IDs

- `MLM` — Mexico
- `MLB` — Brazil / Mercado Livre
- `MLA` — Argentina
- `MLC` — Chile
- `MCO` — Colombia
- `MPE` — Peru
- `MLU` — Uruguay

## Useful provider URL params

- `site_id=MLM`
- `q=laptop`
- `limit=50`
- `offset=0`
- `sort=price_asc` or `price_desc` when supported by the marketplace response
- `min_price=100`
- `min_discount=10`
- `discount_only=true`
- `free_shipping=true`
- `exclude_keywords=used|broken|parts`

## Notes

Mercado Libre does not expose an `original_price` for every listing. Listings without an original price are imported as marketplace products with `oldPrice == currentPrice`, so they may not display a visible discount. When Mercado Libre exposes `original_price` or `base_price`, DiscountHub calculates the real discount.
