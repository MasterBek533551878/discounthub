# Stage 66 — partner click link fix

Fixes outbound click redirects after Awin/Admitad expansion:

- Repairs Admitad AliExpress links before redirecting, so users land on the exact AliExpress product instead of the marketplace homepage.
- Canonicalizes eBay item URLs by stripping noisy search/hash/amdata parameters and redirecting to `/itm/<item_id>`.
- Keeps DiscountHub `/deals/{id}/click` as the single public click endpoint, so click analytics are still recorded.
- Adds `scripts/stage66_check_click_redirects.ps1` for quick redirect verification.

Run backend restart after applying the patch.
