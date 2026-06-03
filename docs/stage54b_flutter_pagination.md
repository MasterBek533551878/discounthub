# Stage 54b — Flutter API pagination hardening

This stage removes the expensive startup behaviour where Flutter loaded many `/deals` pages immediately to build a local cache.

## Changes

- `ApiDealsDataSource.refresh()` now loads only one live page for cache/fallback warm-up.
- `DealsHomePage` uses server-side pagination with endless scroll.
- Product details navigation passes the visible `Deal` object through `GoRouter.extra`, so opening a server-loaded item no longer depends on the full local cache.
- `DealsRepository` remembers recently loaded API deals by id for detail fallback without keeping the full catalog in memory.

## Why

This prepares DiscountHub for many marketplaces and online stores. The app should load filtered pages on demand instead of downloading the entire catalog on launch.

## Expected API pattern after this patch

On launch, you should normally see only a small number of calls like:

- `GET /deals?sort=discount_desc&page=1&page_size=80&currency=USD`
- `GET /deals/facets?currency=USD`

When the user scrolls near the bottom, the app should request:

- `GET /deals?...&page=2&page_size=80...`
- `GET /deals?...&page=3&page_size=80...`
