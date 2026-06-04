# DiscountHub Stage 77 — Admitad official deeplink fallback

This backend-only patch keeps eBay and Awin untouched and changes only Admitad handling.

## Why

Stage 76 proved that DiscountHub can store `ulp=...` on Admitad links, but a real click can still land on the AliExpress homepage. That means the problem is no longer just “missing `ulp`”. It can be one of these:

1. The product URL from the product feed is dead/out of stock and AliExpress redirects it to the homepage.
2. The advertiser/program needs Admitad's official Deeplink Generator API instead of a manually assembled tracking URL.
3. Rewriting every tracking URL to `ad.admitad.com` changes routing for some Admitad shortened domains.

## What changed

- Added `app/services/admitad_deeplink_service.py`.
- On `/deals/{id}/click`, Admitad deals now try the official Admitad Deeplink Generator API first.
- If the API is unavailable, clicks fall back to a manual `ulp` deeplink.
- Manual fallback preserves the original Admitad tracking host/path (`rzekl.com`, `rztekl.com`, or `ad.admitad.com`) instead of rewriting everything to `ad.admitad.com`.
- The generic Admitad target extractor now works for all future Admitad shops, not only AliExpress.

## Important

If both the direct product URL and the official Admitad-generated deeplink still open a homepage or unavailable product page, the feed row itself is bad/stale. In that case, no deeplink template can fix that product; the specific program/feed needs stricter filtering or should be disabled while other Admitad programs can remain enabled.
