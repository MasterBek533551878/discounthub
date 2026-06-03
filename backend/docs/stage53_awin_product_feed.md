# Stage 53 — Awin Product Feed List integration

This stage adds a production-safe Awin importer without breaking the existing eBay pipeline.

## What changed

- Added `awin_feed_list_api` provider adapter.
- Added backend settings for Awin:
  - `AWIN_PUBLISHER_ID`
  - `AWIN_DATAFEED_API_KEY`
  - `AWIN_FEED_LIST_URL`
  - `AWIN_FEED_MAX_FEEDS`
  - `AWIN_FEED_MAX_ITEMS_PER_FEED`
  - `AWIN_FEED_MIN_DISCOUNT_PERCENT`
- Added a disabled provider template in `config/feed_providers.json`:
  - `awin_feed_list`
- Added PowerShell scripts:
  - `scripts/awin_write_env.ps1`
  - `scripts/awin_env_check.ps1`
  - `scripts/awin_feed_list_smoke_test.ps1`
  - `scripts/awin_register_and_sync.ps1`

## How it works

Awin gives a Feed List Download URL. That URL is not usually a product feed itself; it is a list of advertiser feed download URLs.

The new adapter does this:

1. Reads Awin credentials from `.env`.
2. Downloads the Awin Feed List.
3. Finds available product feed download URLs.
4. Downloads only a limited sample from each feed for safety.
5. Normalizes rows through the existing `awin_products` importer.
6. Imports them into DiscountHub like any other feed provider.

## Safe defaults

The default provider URL is:

```text
awin://feed-list?max_feeds=3&max_items_per_feed=80&min_discount_percent=10&joined_only=true
```

This means a first sync imports at most 240 Awin rows before validation/filtering. Increase limits after checking quality.

## Local setup

Run from `backend`:

```powershell
.\scripts\awin_write_env.ps1 -PublisherId "2906853" -DatafeedApiKey "PASTE_SECRET_KEY_HERE" -FeedListUrl "PASTE_FULL_FEED_LIST_URL_OPTIONAL"
.\scripts\awin_env_check.ps1
```

Restart the backend after editing `.env`.

Then test Awin feed-list reachability:

```powershell
.\scripts\awin_feed_list_smoke_test.ps1
```

If at least one advertiser is already joined and has `Product Feed = Yes`, register and sync:

```powershell
.\scripts\awin_register_and_sync.ps1 -MaxFeeds 3 -MaxItemsPerFeed 80 -MinDiscountPercent 10 -TimeoutSeconds 60
```

If advertisers are still Pending, the smoke test can work while sync imports nothing. That is expected until Awin exposes usable product feeds.

## Production note

Do not commit `.env` or full Awin feed-list URLs. The feed-list URL contains a secret token.
