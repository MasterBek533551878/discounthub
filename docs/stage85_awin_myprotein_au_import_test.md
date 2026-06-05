# DiscountHub Stage 85 — Awin Myprotein AU import test

Goal: import only the joined Awin advertiser **Myprotein AU** (`advertiser_id=19155`) instead of syncing all Awin feeds.

Why: Stage 80 diagnostics showed Myprotein AU has a product feed with many rows passing DiscountHub discount rules, while Decathlon Ireland currently has `passed=0` because it lacks an old/current price pair in the sampled rows.

Changes:
- `backend/app/services/awin_feed_list_service.py`
  - adds optional `advertiser_id` / `merchant_id` and `advertiser_name` / `merchant_name` filters to `awin://feed-list?...` provider URLs;
  - keeps the existing safety limits: joined-only feeds, max feed count, max rows per feed, minimum discount percent.
- `scripts/stage85_awin_myprotein_au_import_test.ps1`
  - registers provider `awin_myprotein_au_v1`;
  - syncs only Myprotein AU;
  - prints sample imported deals and `/deals/{id}/click` browser-test commands.

Provider URL example:

```text
awin://feed-list?advertiser_id=19155&advertiser_name=Myprotein%20AU&max_feeds=5&max_items_per_feed=500&min_discount_percent=10&joined_only=true
```

This stage is backend-only. Android/iOS rebuild is not required for local testing.
