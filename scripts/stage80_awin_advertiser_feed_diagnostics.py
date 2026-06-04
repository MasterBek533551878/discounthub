from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

FEED_URL_KEYS = (
    "download_url", "feed_url", "product_feed_url", "feed_download_url",
    "example_download_url", "example_url", "url", "downloadurl", "feedurl",
    "productfeedurl", "feeddownloadurl", "exampledownloadurl", "exampleurl",
)
ADVERTISER_KEYS = (
    "advertiser_name", "merchant_name", "programme_name", "program_name",
    "advertiser", "merchant", "name",
)
ADVERTISER_ID_KEYS = (
    "advertiser_id", "merchant_id", "programme_id", "program_id", "id",
)
STATUS_KEYS = (
    "relationship_status", "membership_status", "publisher_status",
    "programme_status", "program_status", "joined_status", "status",
)
REGION_KEYS = ("programme_region", "program_region", "region", "country", "market")
LANGUAGE_KEYS = ("feed_language", "language", "lang")

TITLE_KEYS = ("product_name", "productName", "productname", "aw_product_name", "name", "title")
LINK_KEYS = (
    "aw_deep_link", "deep_link", "deepLink", "deeplink", "affiliate_url",
    "tracking_url", "tracking_link", "merchant_deep_link", "merchant_product_url",
    "product_url", "productUrl", "product_link", "click_url", "clickout_url",
    "link", "url",
)
IMAGE_KEYS = (
    "merchant_image_url", "aw_image_url", "aw_thumb_url", "large_image",
    "image_url", "image_link", "imageUrl", "thumbnail", "thumbnail_url",
    "merchant_thumb_url", "picture", "image",
)
STOCK_KEYS = (
    "in_stock", "stock_status", "availability", "g:availability", "g_availability",
    "available", "availability_status",
)

SALE_PRICE_KEYS = (
    "sale_price", "saleprice", "discount_price", "discounted_price", "offer_price",
    "now_price", "current_price", "currentprice",
)
LISTED_PRICE_KEYS = (
    "product_price", "search_price", "store_price", "price", "normal_price",
    "normalprice", "amount", "price_value",
)
OLD_PRICE_KEYS = (
    "product_price_old", "productpriceold", "rrp_price", "rrp", "old_price",
    "oldprice", "was_price", "wasprice", "list_price", "listprice",
    "original_price", "originalprice", "retail_price", "retailprice", "regular_price",
    "regularprice", "previous_price", "previousprice", "before_price",
    "strikethrough_price", "compare_at_price",
)
SAVING_AMOUNT_KEYS = ("saving", "savings", "saving_amount", "savings_amount", "discount_amount", "amount_saved")
SAVING_PERCENT_KEYS = (
    "savings_percent", "saving_percent", "discount_percent", "discount_percentage",
    "percentage_discount", "percent_discount",
)


def read_env(path: str) -> dict[str, str]:
    values: dict[str, str] = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                    value = value[1:-1]
                values[key.strip()] = value
    for key, value in os.environ.items():
        if key.startswith("AWIN_"):
            values[key] = value
    return values


def normalize_header(value: str) -> str:
    value = value.strip().lower()
    value = value.replace("g:", "g_")
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def pick_string(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return str(row[key]).strip()
        normalized = normalize_header(key)
        if normalized in row and row[normalized] not in (None, ""):
            return str(row[normalized]).strip()
    return ""


def pick_number(row: dict[str, Any], *keys: str) -> float | None:
    raw = pick_string(row, *keys)
    if not raw:
        return None
    text = raw.strip()
    # Handle values like "USD 12.34", "1,234.56", "12,34".
    text = re.sub(r"[^0-9,\.\-]", "", text)
    if not text or text in ("-", ".", ","):
        return None
    if "," in text and "." in text:
        text = text.replace(",", "")
    elif "," in text and "." not in text:
        text = text.replace(",", ".")
    try:
        value = float(text)
    except ValueError:
        return None
    return value if value > 0 else None


def fetch_bytes(url: str, timeout: int) -> tuple[bytes, str, str]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json,text/csv,text/tab-separated-values,*/*",
            "User-Agent": "DiscountHub-Awin-Diagnostics/0.1",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("content-type", "") or ""
        content_encoding = (response.headers.get("content-encoding", "") or "").lower()
        charset = response.headers.get_content_charset() or "utf-8"
        data = response.read()
    if content_encoding == "gzip" or data.startswith(b"\x1f\x8b") or url.lower().split("?")[0].endswith(".gz"):
        data = gzip.decompress(data)
    return data, content_type.lower(), charset


def fetch_text(url: str, timeout: int, max_bytes: int | None = None) -> tuple[str, str]:
    data, content_type, charset = fetch_bytes(url, timeout)
    if max_bytes is not None and len(data) > max_bytes:
        data = data[:max_bytes]
    return data.decode(charset, errors="replace"), content_type


def extract_items(raw_body: str, *, feed_url: str, content_type: str) -> list[dict[str, Any]]:
    stripped = raw_body.lstrip("\ufeff\n\r\t ")
    looks_json = stripped.startswith(("[", "{")) or "json" in content_type
    looks_tsv = feed_url.lower().split("?")[0].endswith(".tsv") or "tab-separated" in content_type
    if looks_json:
        data = json.loads(raw_body)
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if isinstance(data, dict):
            for key in ("feeds", "items", "products", "data", "results"):
                if isinstance(data.get(key), list):
                    return [x for x in data[key] if isinstance(x, dict)]
        return []
    delimiter = "\t" if looks_tsv else None
    sample = raw_body[:8192]
    if delimiter is None:
        try:
            delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
        except csv.Error:
            delimiter = ","
    reader = csv.DictReader(io.StringIO(raw_body), delimiter=delimiter)
    if not reader.fieldnames:
        return []
    headers = [str(h or "").strip() for h in reader.fieldnames]
    items: list[dict[str, Any]] = []
    for row in reader:
        item: dict[str, Any] = {}
        for raw_key, value in row.items():
            key = str(raw_key or "").strip()
            if not key:
                continue
            item[key] = value.strip() if isinstance(value, str) else value
        for header in headers:
            if header and header in item:
                item.setdefault(normalize_header(header), item[header])
        if any(v not in (None, "") for v in item.values()):
            items.append(item)
    return items


def pick_url(row: dict[str, Any]) -> str:
    direct = pick_string(row, *FEED_URL_KEYS)
    if direct.startswith(("http://", "https://")):
        return direct
    for value in row.values():
        if isinstance(value, str) and value.strip().startswith(("http://", "https://")):
            return value.strip()
    return ""


def looks_joined(row: dict[str, Any]) -> bool:
    status_text = " ".join(
        str(row.get(k, "")).strip().lower()
        for k in STATUS_KEYS
        if row.get(k) not in (None, "")
    )
    if not status_text:
        return True
    if any(v in status_text for v in ("pending", "rejected", "declined", "suspended", "closed", "not joined", "not_joined")):
        return False
    return any(v in status_text for v in ("joined", "approved", "active", "allowed", "accepted", "yes", "true"))


def derive_old_price(current: float | None, saving_amount: float | None, saving_percent: float | None) -> float | None:
    if not current or current <= 0:
        return None
    if saving_amount and saving_amount > 0:
        return current + saving_amount
    if saving_percent and 0 < saving_percent < 100:
        return current / (1 - saving_percent / 100)
    return None


def awin_price_pair(item: dict[str, Any]) -> tuple[float | None, float | None]:
    sale_price = pick_number(item, *SALE_PRICE_KEYS)
    listed_price = pick_number(item, *LISTED_PRICE_KEYS)
    old_price = pick_number(item, *OLD_PRICE_KEYS)
    saving_amount = pick_number(item, *SAVING_AMOUNT_KEYS)
    saving_percent = pick_number(item, *SAVING_PERCENT_KEYS)
    if sale_price and sale_price > 0:
        current = sale_price
        if old_price and old_price > current:
            return current, old_price
        if listed_price and listed_price > current:
            return current, listed_price
        return current, derive_old_price(current, saving_amount, saving_percent) or old_price or listed_price
    current = listed_price
    if current and current > 0 and (not old_price or old_price <= current):
        derived = derive_old_price(current, saving_amount, saving_percent)
        if derived and derived > current:
            return current, derived
    return current, old_price


def filter_stats(items: list[dict[str, Any]], min_discount_percent: int) -> dict[str, Any]:
    stats: dict[str, Any] = {
        "rows": len(items),
        "missing_title": 0,
        "missing_link": 0,
        "missing_image": 0,
        "missing_current_price": 0,
        "out_of_stock": 0,
        "no_discount_price_pair": 0,
        "below_min_discount": 0,
        "passed": 0,
        "example_passed_title": "",
        "headers": sorted({str(k) for item in items[:3] for k in item.keys()})[:50],
    }
    for item in items:
        title = pick_string(item, *TITLE_KEYS)
        link = pick_string(item, *LINK_KEYS)
        image = pick_string(item, *IMAGE_KEYS)
        current, old = awin_price_pair(item)
        stock_text = (pick_string(item, *STOCK_KEYS) or "").lower()
        if not title:
            stats["missing_title"] += 1
            continue
        if not link:
            stats["missing_link"] += 1
            continue
        if not image:
            stats["missing_image"] += 1
            continue
        if not current or current <= 0:
            stats["missing_current_price"] += 1
            continue
        if stock_text and any(v in stock_text for v in ("false", "no", "out", "unavailable", "0")):
            stats["out_of_stock"] += 1
            continue
        if not old or old <= current:
            stats["no_discount_price_pair"] += 1
            continue
        discount = round(((old - current) / old) * 100)
        if discount <= 0 or discount < min_discount_percent:
            stats["below_min_discount"] += 1
            continue
        stats["passed"] += 1
        if not stats["example_passed_title"]:
            stats["example_passed_title"] = title[:120]
    return stats


def prepare_feed_url(url: str, env: dict[str, str]) -> str:
    api_key = env.get("AWIN_DATAFEED_API_KEY", "")
    publisher_id = env.get("AWIN_PUBLISHER_ID", "")
    replacements = {
        "YOUR_API_KEY": api_key,
        "{api_key}": api_key,
        "{apikey}": api_key,
        "[api_key]": api_key,
        "[apikey]": api_key,
        "<api_key>": api_key,
        "<apikey>": api_key,
        "YOUR_PUBLISHER_ID": publisher_id,
        "{publisher_id}": publisher_id,
        "[publisher_id]": publisher_id,
        "<publisher_id>": publisher_id,
    }
    resolved = url
    for key, value in replacements.items():
        if value:
            resolved = resolved.replace(key, urllib.parse.quote(value))
    return resolved


@dataclass
class FeedRow:
    advertiser: str
    advertiser_id: str
    region: str
    language: str
    status: str
    feed_url: str

    @property
    def display(self) -> str:
        parts = [self.advertiser or "Awin advertiser"]
        if self.region:
            parts.append(self.region)
        if self.advertiser_id:
            parts.append(f"id={self.advertiser_id}")
        return " / ".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose Awin joined advertisers/product feeds without importing into DB.")
    parser.add_argument("--env", default="backend/.env")
    parser.add_argument("--max-feeds", type=int, default=25)
    parser.add_argument("--max-rows", type=int, default=200)
    parser.add_argument("--min-discount", type=int, default=10)
    parser.add_argument("--joined-only", action="store_true", default=True)
    parser.add_argument("--include-not-joined", action="store_true")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    env = read_env(args.env)
    key = env.get("AWIN_DATAFEED_API_KEY", "")
    feed_list_url = env.get("AWIN_FEED_LIST_URL", "")
    template = env.get("AWIN_FEED_LIST_ENDPOINT_TEMPLATE", "https://productdata.awin.com/datafeed/list/apikey/{api_key}")
    if not key and not feed_list_url:
        print(f"ERROR: AWIN_DATAFEED_API_KEY or AWIN_FEED_LIST_URL is missing in {args.env}", file=sys.stderr)
        return 2
    if not feed_list_url:
        feed_list_url = template.format(
            api_key=urllib.parse.quote(key),
            publisher_id=urllib.parse.quote(env.get("AWIN_PUBLISHER_ID", "")),
        )

    print("== DiscountHub Stage 80: Awin advertiser feed diagnostics ==")
    print(f"Env: {args.env}")
    print(f"Joined only: {not args.include_not_joined}")
    print(f"Max feeds: {args.max_feeds}; max rows/feed: {args.max_rows}; min discount: {args.min_discount}%")
    print("")

    try:
        body, content_type = fetch_text(feed_list_url, timeout=args.timeout)
        rows = extract_items(body, feed_url=feed_list_url, content_type=content_type)
    except Exception as exc:
        print(f"ERROR: Could not fetch/parse Awin feed list: {exc}", file=sys.stderr)
        return 1

    print(f"Feed-list rows: {len(rows)}")
    feeds: list[FeedRow] = []
    skipped_no_url = 0
    skipped_status = 0
    seen_urls: set[str] = set()
    for row in rows:
        url = pick_url(row)
        if not url:
            skipped_no_url += 1
            continue
        if url in seen_urls:
            continue
        if not args.include_not_joined and not looks_joined(row):
            skipped_status += 1
            continue
        seen_urls.add(url)
        feeds.append(FeedRow(
            advertiser=pick_string(row, *ADVERTISER_KEYS) or "Awin advertiser",
            advertiser_id=pick_string(row, *ADVERTISER_ID_KEYS),
            region=pick_string(row, *REGION_KEYS),
            language=pick_string(row, *LANGUAGE_KEYS),
            status=" ".join(pick_string(row, k) for k in STATUS_KEYS if pick_string(row, k)),
            feed_url=url,
        ))
        if len(feeds) >= args.max_feeds:
            break

    print(f"Selected feeds: {len(feeds)} (skipped no-url={skipped_no_url}, skipped status={skipped_status})")
    print("")
    if not feeds:
        return 0

    total_passed = 0
    for i, feed in enumerate(feeds, start=1):
        print("-" * 100)
        print(f"[{i}] {feed.display}")
        if feed.status:
            print(f"    status: {feed.status}")
        safe_url = prepare_feed_url(feed.feed_url, env)
        try:
            # Product feeds are usually delimited. The backend streams rows; here we fetch safely with a cap.
            text, product_content_type = fetch_text(safe_url, timeout=args.timeout, max_bytes=10 * 1024 * 1024)
            # Keep header + max rows to match backend safety behavior even if we fetched more.
            if not (text.lstrip().startswith(("[", "{")) or "json" in product_content_type):
                lines = text.splitlines(True)
                text = "".join(lines[: args.max_rows + 1])
            items = extract_items(text, feed_url=safe_url, content_type=product_content_type)[: args.max_rows]
            stats = filter_stats(items, min_discount_percent=args.min_discount)
            total_passed += int(stats["passed"])
            print(
                "    rows={rows}, passed={passed}, missing_title={missing_title}, missing_link={missing_link}, "
                "missing_image={missing_image}, missing_price={missing_current_price}, no_discount_pair={no_discount_price_pair}, "
                "below_min_discount={below_min_discount}, out_of_stock={out_of_stock}".format(**stats)
            )
            if stats["example_passed_title"]:
                print(f"    example passed: {stats['example_passed_title']}")
            print(f"    headers: {', '.join(stats['headers'][:18])}")
        except Exception as exc:
            print(f"    ERROR: {exc}")

    print("-" * 100)
    print(f"Total rows that would pass DiscountHub rules in this sample: {total_passed}")
    if total_passed == 0:
        print("No sampled rows passed. Common reasons: no product feed URL, no old/current price pair, missing image/link, out of stock, or discount below threshold.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
