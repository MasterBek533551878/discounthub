# Stage 54 — Flutter filters from backend facets

This stage connects Flutter filtering UI to the Stage 53 backend contract.

## What changed

- Flutter can read `GET /deals/facets`.
- Home feed requests filtered pages through `GET /deals` instead of relying only on locally cached deals.
- Marketplace, category, country and monetization filters can show backend counts.
- The advanced filter sheet has marketplace search, so it remains usable when many stores are connected.
- `Deal` now accepts backend metadata: `providerId`, `monetizationMode`, `hotDeal`, `lowestPrice`, `dealScore`.

## Notes

Stage 54 is backward compatible. If `/deals/facets` is unavailable, Flutter falls back to cached/local deal-derived facets.

Before publishing this app build, deploy Stage 53 backend changes to production so `https://api.discounthub.uz/deals/facets` is available.
