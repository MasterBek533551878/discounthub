# Stage 72 - eBay global click fallback

Some regional eBay item pages opened eBay's generic "Sorry" page in browser tests even when the listing came from the Browse API and had a valid item id. Stage 72 keeps marketplace labels and catalog facets unchanged, but normalizes eBay click redirects to a safer global `https://www.ebay.com/itm/<item_id>` URL, except `ebay.es`, which was verified as working and is preserved.

No database resync is required. The `/deals/{id}/click` endpoint computes this at click time.
