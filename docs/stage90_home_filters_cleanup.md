# Stage 90 — Home filters cleanup

Goal: simplify the main deals filter sheet before the next release.

Changes:

- Removed delivery-related filters from the main feed filter sheet:
  - delivery region
  - ships-to country
  - free shipping only
- Removed low-value quality filters from the sheet:
  - minimum rating
  - verified deals only
- Kept the filters users actually need for DiscountHub MVP:
  - store / marketplace
  - category
  - minimum discount
  - price limit
- Added sorting to the filter sheet:
  - biggest discount
  - best match
  - newest
  - lowest price
  - highest price
- Extended minimum discount choices with 10% and 70%.

The backend API still supports the old delivery parameters for compatibility, but the Flutter main feed no longer sends or exposes them.
