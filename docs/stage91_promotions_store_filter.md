# Stage 91 — Promotions store filter

Adds a store filter to the Flutter promotions tab.

## Scope

- Passes a `store` query parameter from Flutter to the existing backend `/promotions` endpoint.
- Keeps a local list of stores seen in imported promotions.
- Adds horizontal store chips below the promo type chips:
  - All stores
  - One chip per store, for example AliExpress PL or Navimow FR

## Notes

The backend already supports `store` filtering in `/promotions`, so this patch only updates Flutter API/query/UI wiring.
