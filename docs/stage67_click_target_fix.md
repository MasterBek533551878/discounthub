# Stage 67 click target fix

Fixes outbound click target selection for marketplace-specific links.

- eBay: prefer a canonical product URL derived from the product URL, not a noisy affiliate/search URL.
- Admitad/AliExpress: preserve Admitad tracking while forcing `ulp` to a clean AliExpress item URL.
- Adds a redirect checker that does not follow external marketplace redirects, so it prints the first `Location` header from the backend.
