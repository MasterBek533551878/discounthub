# Stage 91 — TTfone Awin quality patch

Purpose: keep TTfone enabled safely without re-importing the 9 manually confirmed 404 product rows and clean common Awin mojibake in product titles/descriptions.

Changes:
- `backend/app/services/awin_feed_list_service.py` blocks 9 confirmed bad TTfone Awin product IDs for advertiser `28737`.
- `backend/app/services/feed_adapters.py` cleans common Awin mojibake like `Â£` -> `£`, broken quotes/dashes/bullets/euro symbols in Awin product title/description/platform/category text.

After deploy, re-enable `awin_ttfone_v1` and sync. Expected TTfone public total is about 205, not 214.
