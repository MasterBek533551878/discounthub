# Stage 89c - Promotions response text cleanup

Adds a final safety layer in `PromotionsService`:

- repairs Awin promotion mojibake before storing rows;
- repairs existing DB rows when returning `/promotions` responses;
- provides a one-off local SQLite cleanup script;
- provides an API verification script for Navimow promotion text.

This is intentionally limited to the promotions pipeline and does not touch product deal titles.
