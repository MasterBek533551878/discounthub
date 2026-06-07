# Stage 89b — Awin promo Euro mojibake cleanup

Fixes remaining incomplete Euro-sign mojibake in Awin promotions, for example:

- `â¬200 OFF` -> `€200 OFF`
- `â¬300 OFF` -> `€300 OFF`
- `â¬400 OFF` -> `€400 OFF`

Also re-cleans extracted `discount_text` before storing promotions.

Run the usual Stage 88 sync again after applying this patch. Existing `awin:*` promotion rows will be updated in-place.
