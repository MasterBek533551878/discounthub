# Stage 83 — AliExpress WW nested deeplink diagnostics

Dry-run diagnostics only. This stage does not import, delete, or update production data.

Purpose:

- Stream a small number of rows from the Admitad AliExpress WW feed.
- Detect whether feed links use this structure:
  `rzekl.com -> ulp=s.click.aliexpress.com/deep_link.htm -> dl_target_url=aliexpress.com/item/...`
- Extract the clean product URL from nested `dl_target_url`.
- Confirm whether the original affiliate URL should be preserved instead of being simplified.

Expected finding if the theory is correct:

- `dl_target_found > 0`
- `clean_item_found > 0`
- original affiliate URL already contains `s.click.aliexpress.com/deep_link.htm`
- nested target contains `www.aliexpress.com/item/<id>.html`

If this is confirmed, the next safe production patch should:

1. Preserve the original Admitad affiliate URL from the feed.
2. Extract `productUrl` from nested `dl_target_url`.
3. Do not replace the working feed URL with a simplified `rzekl.com/?ulp=<productUrl>` URL.
4. Continue to keep AliExpress WW disabled until click tests pass.
