# Stage 71 — eBay import quality filters

This patch moves eBay cleanup earlier in the pipeline: low-quality eBay listings are rejected during Browse API import instead of being removed later.

The eBay Browse adapter now rejects obvious non-product or bad UX listings such as auctions-only, parts-only, missing images, missing item URLs, ended listings, weak seller feedback where available, and unrealistic discount ranges.

Recommended workflow:

1. Dry run:
   `./scripts/stage71_harden_ebay_import_filters.ps1`
2. Apply DB URL hardening and purge old eBay rows:
   `./scripts/stage71_harden_ebay_import_filters.ps1 -Apply`
3. Resync eBay providers with the new filters:
   `./scripts/stage71_harden_ebay_import_filters.ps1 -Apply -Sync -LimitProviders 12 -TimeoutSeconds 90`

Run without `-LimitProviders` only when you are ready to sync all enabled eBay providers.
