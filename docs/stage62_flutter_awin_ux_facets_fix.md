# DiscountHub Stage 62 - Flutter Awin UX/facets fix

This patch fixes the confusing Flutter UI state after importing a large Awin feed.

## Changes

- Removes the hero banner count text like "36 актуальных предложений" and replaces it with a neutral CTA.
- Updates the hero subtitle so it is not eBay-only anymore.
- Avoids replacing backend facet counts with the first loaded page of 36 deals when `/deals/facets` fails or times out.
- Increases Flutter API timeout to 20 seconds to make `/deals/facets` more reliable after large imports.
- Rewords the advanced filters helper text to remove developer/backend wording.
- Changes paging footer wording from "актуальных предложений" to a neutral "предложений".

## Why

After Awin import, the backend can have 14k+ deals, but the first Flutter page still loads 36 items for performance. The UI must not present that first page as the full catalogue.

