from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from fastapi import HTTPException

from app.services.awin_feed_list_service import AwinFeedListService


def build_provider_url(args: argparse.Namespace) -> str:
    query: dict[str, str] = {
        "max_feeds": str(args.max_feeds),
        "max_feeds_per_advertiser": str(args.max_feeds_per_advertiser),
        "max_items_per_feed": str(args.max_items_per_feed),
        "max_scan_rows_per_feed": str(args.max_scan_rows_per_feed),
        "min_discount_percent": str(args.min_discount_percent),
        "joined_only": "true",
    }
    if args.advertiser_id:
        query["advertiser_id"] = args.advertiser_id
    if args.advertiser_name:
        query["advertiser_name"] = args.advertiser_name
    return "awin://feed-list?" + urllib.parse.urlencode(query)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit Awin feed coverage without printing credentials or feed URLs.",
    )
    parser.add_argument("--advertiser-id", default="")
    parser.add_argument("--advertiser-name", default="")
    parser.add_argument("--max-feeds", type=int, default=60)
    parser.add_argument("--max-feeds-per-advertiser", type=int, default=5)
    parser.add_argument("--max-items-per-feed", type=int, default=500)
    parser.add_argument("--max-scan-rows-per-feed", type=int, default=25000)
    parser.add_argument("--min-discount-percent", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args()

    service = AwinFeedListService()
    provider_url = build_provider_url(args)
    options = service._parse_options(provider_url)

    try:
        feed_list_url = service._resolve_feed_list_url(provider_url)
        list_body, list_content_type = service._fetch_text(feed_list_url, timeout_seconds=args.timeout)
        feed_rows = service._extract_items_from_body(
            list_body,
            feed_url=feed_list_url,
            content_type=list_content_type,
        )
        selected_feeds = service._select_feed_rows(feed_rows, options=options)
    except HTTPException as exc:
        print(json.dumps({"status": "error", "detail": exc.detail}, ensure_ascii=False))
        return 1

    totals = {
        "selectedFeeds": len(selected_feeds),
        "checkedFeeds": 0,
        "failedFeeds": 0,
        "scannedRows": 0,
        "passedRows": 0,
        "returnedRows": 0,
    }

    for index, feed in enumerate(selected_feeds, start=1):
        result: dict[str, object] = {
            "feedIndex": index,
            "advertiserId": feed.advertiser_id,
            "advertiser": feed.advertiser_name,
            "feedName": feed.feed_name,
            "region": feed.region,
            "language": feed.language,
        }
        try:
            _items, stats = service._fetch_filtered_product_items(
                service._prepare_feed_download_url(feed.feed_url),
                timeout_seconds=args.timeout,
                max_items=options.max_items_per_feed,
                max_scan_rows=options.max_scan_rows_per_feed,
                min_discount_percent=options.min_discount_percent,
            )
            result.update(
                {
                    "status": "ok",
                    "scannedRows": stats.get("scanned_rows", stats.get("rows", 0)),
                    "passedRows": stats.get("passed", 0),
                    "returnedRows": stats.get("returned", 0),
                    "missingTitle": stats.get("missing_title", 0),
                    "missingLink": stats.get("missing_link", 0),
                    "missingImage": stats.get("missing_image", 0),
                    "missingCurrentPrice": stats.get("missing_current_price", 0),
                    "noDiscountPricePair": stats.get("no_discount_price_pair", 0),
                    "belowMinDiscount": stats.get("below_min_discount", 0),
                    "outOfStock": stats.get("out_of_stock", 0),
                    "restrictedOffer": stats.get("restricted_offer", 0),
                    "headers": stats.get("headers", []),
                }
            )
            totals["checkedFeeds"] += 1
            totals["scannedRows"] += int(result["scannedRows"] or 0)
            totals["passedRows"] += int(result["passedRows"] or 0)
            totals["returnedRows"] += int(result["returnedRows"] or 0)
        except HTTPException as exc:
            totals["failedFeeds"] += 1
            result.update({"status": "error", "detail": exc.detail})
        except Exception as exc:  # Defensive diagnostics only.
            totals["failedFeeds"] += 1
            result.update({"status": "error", "detail": str(exc)})

        print(json.dumps(result, ensure_ascii=False))

    print(json.dumps({"status": "summary", **totals}, ensure_ascii=False))
    return 0 if selected_feeds else 1


if __name__ == "__main__":
    raise SystemExit(main())
