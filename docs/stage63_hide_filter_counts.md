# DiscountHub Stage 63 — hide filter counts

Removes customer-facing item counters from filter chips.

The backend facet counts are still loaded and can still be used internally for ordering/filter availability, but the UI now displays only clean labels such as `AliExpress PL`, `eBay US`, `Fashion`, `Other`, and `All`.

Changed file:

- `lib/features/deals/widgets/deal_filter_sheet.dart`
