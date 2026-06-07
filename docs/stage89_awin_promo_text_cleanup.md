# Stage 89 - Awin promotion text cleanup

This hotfix keeps Stage 88 intact and only improves imported Awin promotion text.

Changes:
- Repairs common Awin mojibake in promotion title/description/discount text, for example `Letnia WyprzedaÅ¼` -> `Summer Sale` and `â‚¬200 OFF` -> `€200 OFF`.
- Adds a narrow filter for low-value non-discount offers such as free-shipping-only or gift-only offers, while keeping real sale/coupon offers.
- Forces UTF-8 output in the Stage 88 PowerShell sync script so local logs are easier to read.

After applying the patch, re-run `scripts/stage88_sync_awin_promotions.ps1`; existing `awin:*` promotion IDs are upserted, so the cleaned text replaces old rows.
