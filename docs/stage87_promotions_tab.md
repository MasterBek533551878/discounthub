# Stage 87 — Promotions tab foundation

This stage adds the first safe foundation for DiscountHub **Акции / Promos**.

## Product decision

The app keeps concrete discounted products in the main feed. The new bottom-tab section is reserved for store-level offers:

- promo codes (`coupon`)
- store/category sales (`sale`)
- short-time sales with an end date (`flash_sale`)

The following offer types are intentionally not added yet: gifts with purchase, free shipping, bundles / 2+1, cashback, trade-in, and refurbished-only comparisons.

## Backend

New public endpoints:

- `GET /promotions`
- `GET /promotions/{promotion_id}`
- `GET /promotions/{promotion_id}/click`

New SQLite tables:

- `promotions`
- `promotion_click_events`

The API returns only currently active promotions:

- `valid_from` is empty or in the past
- `valid_until` is empty or in the future

No fake promotions are seeded. The tab will stay empty until a real promotions source, such as Awin Offers, imports records into `promotions`.

## Flutter

The bottom navigation now has three tabs:

1. Deals / Главная
2. Promos / Акции
3. Settings / Настройки

The Promotions page supports search, type filters, promo-code copying, and tracked outbound clicks through `/promotions/{id}/click`.
