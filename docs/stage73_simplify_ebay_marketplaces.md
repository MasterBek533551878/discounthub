# Stage 73 — Simplify eBay marketplaces

Customer-facing marketplace filters should not expose every eBay regional Browse API source. This stage keeps only stable eBay US and eBay ES sources, groups eBay Motors into eBay US, disables regional eBay providers that produced bad browser UX, and removes tiny legacy placeholder stores such as Amazon/AliExpress/Alibaba when they only create empty-looking filters.

The backend still supports provider-level separation internally. The Flutter filter displays `eBay 🇺🇸` and `eBay 🇪🇸` while keeping the original API values (`eBay US`, `eBay ES`) for queries.
