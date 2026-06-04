# Stage 80 — Awin advertiser feed diagnostics

This stage adds a read-only diagnostic script for joined Awin advertisers.

It does not import or delete deals. It checks each visible Awin product feed and reports why sampled rows would or would not pass DiscountHub import rules:

- missing product title
- missing link
- missing image
- missing current price
- out of stock
- no old/current discount price pair
- discount below threshold
- passed rows

Use it to confirm whether joined Awin advertisers are absent because they have no product feed, no discounted rows, or unsupported/incomplete feed fields.
