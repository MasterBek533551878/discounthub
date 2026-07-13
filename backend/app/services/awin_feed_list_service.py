from __future__ import annotations

import csv
import gzip
import io
import itertools
import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.services.restricted_offer_filter import restricted_offer_match_for_mapping


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AwinFeedListOptions:
    max_feeds: int
    max_feeds_per_advertiser: int
    max_items_per_feed: int
    max_scan_rows_per_feed: int
    min_discount_percent: int
    joined_only: bool
    advertiser_id: str = ""
    advertiser_name: str = ""
    excluded_advertiser_ids: tuple[str, ...] = ()


class AwinFeedListService:
    """Downloads Awin's Feed List and expands it into product rows.

    Awin has two related things:
      1) Feed List Download: a list of advertiser/product-feed download URLs.
      2) Product feed download URLs: CSV/TSV/JSON product rows for each advertiser.

    The normal feed importer can already normalize `awin_products` rows. This
    service is the bridge that turns one Awin feed-list provider into rows from
    several available advertiser feeds, with safety limits so a fresh sync cannot
    accidentally download a huge catalogue.
    """

    _FEED_URL_KEYS = (
        "download_url",
        "feed_url",
        "product_feed_url",
        "feed_download_url",
        "example_download_url",
        "example_url",
        "url",
        "downloadurl",
        "feedurl",
        "productfeedurl",
        "feeddownloadurl",
        "exampledownloadurl",
        "exampleurl",
    )
    _ADVERTISER_KEYS = (
        "advertiser_name",
        "merchant_name",
        "programme_name",
        "program_name",
        "advertiser",
        "merchant",
        "name",
    )
    _ADVERTISER_ID_KEYS = (
        "advertiser_id",
        "merchant_id",
        "programme_id",
        "program_id",
        "id",
    )
    _STATUS_KEYS = (
        "relationship_status",
        "membership_status",
        "publisher_status",
        "programme_status",
        "program_status",
        "joined_status",
        "status",
    )
    _REGION_KEYS = ("programme_region", "program_region", "region", "country", "market")
    _LANGUAGE_KEYS = ("feed_language", "language", "lang")

    # Some advertiser feeds can contain recently deleted/unavailable Shopify
    # variants even though the Awin feed itself is still downloadable. Keep this
    # blocklist narrow and explicit so one broken advertiser does not affect
    # other Awin stores. IDs below were manually verified as TTfone 404s on
    # production on 2026-06-09.
    _BLOCKED_AWIN_PRODUCTS: set[tuple[str, str]] = {
        ("28737", "42338245511"),
        ("28737", "42338245487"),
        ("28737", "42338245486"),
        ("28737", "42338245485"),
        ("28737", "42338245484"),
        ("28737", "42338245483"),
        ("28737", "42338245482"),
        ("28737", "44290852484"),
        ("28737", "44237432484"),
    }
    _BLOCKED_TITLE_PREFIXES_BY_ADVERTISER: dict[str, tuple[str, ...]] = {
        # TTfone Return/Returned Resale listings can be valid discounted
        # products. Only individually confirmed broken product IDs are blocked.
        "28737": (),
    }

    def search_from_provider_url(self, provider_url: str, *, timeout_seconds: int = 20) -> list[dict[str, Any]]:
        options = self._parse_options(provider_url)
        feed_list_url = self._resolve_feed_list_url(provider_url)
        list_body, list_content_type = self._fetch_text(feed_list_url, timeout_seconds=timeout_seconds)
        feed_rows = self._extract_items_from_body(list_body, feed_url=feed_list_url, content_type=list_content_type)
        selected_feeds = self._select_feed_rows(feed_rows, options=options)

        if not selected_feeds:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Awin feed list did not expose any usable product-feed URLs yet. "
                    "Wait until advertisers are Joined, make sure Product Feed=Yes, or lower joined_only in the provider URL."
                ),
            )

        all_items_by_key: dict[str, dict[str, Any]] = {}
        diagnostics: list[str] = []
        for index, feed_row in enumerate(selected_feeds, start=1):
            feed_url = self._prepare_feed_download_url(feed_row.feed_url)
            try:
                product_items, stats = self._fetch_filtered_product_items(
                    feed_url,
                    timeout_seconds=timeout_seconds,
                    max_items=options.max_items_per_feed,
                    max_scan_rows=options.max_scan_rows_per_feed,
                    min_discount_percent=options.min_discount_percent,
                )
                diagnostics.append(self._format_filter_stats(feed_row, stats))
                if not product_items:
                    continue

                blocked_count = 0
                duplicate_count = 0
                for product in product_items:
                    product.setdefault("_awin_feed_index", index)
                    product.setdefault("_awin_feed_name", feed_row.feed_name)
                    product.setdefault("_awin_feed_region", feed_row.region)
                    product.setdefault("_awin_feed_language", feed_row.language)
                    product.setdefault("_awin_advertiser_id", feed_row.advertiser_id)
                    product.setdefault("_awin_advertiser_name", feed_row.advertiser_name)
                    if self._is_blocked_awin_product(product):
                        blocked_count += 1
                        continue

                    product_key = self._product_dedupe_key(product)
                    if product_key in all_items_by_key:
                        duplicate_count += 1
                        continue
                    all_items_by_key[product_key] = product

                if blocked_count:
                    diagnostics.append(f"{feed_row.display_name}: blocked_known_bad_products={blocked_count}")
                if duplicate_count:
                    diagnostics.append(f"{feed_row.display_name}: duplicate_products={duplicate_count}")
            except HTTPException as exc:
                diagnostics.append(f"{feed_row.display_name}: fetch_error={exc.detail}")
            except Exception as exc:  # pragma: no cover - defensive safety around external feeds.
                diagnostics.append(f"{feed_row.display_name}: unexpected_error={exc}")

        all_items = list(all_items_by_key.values())
        if diagnostics:
            logger.info("Awin product-feed diagnostics: %s", " | ".join(diagnostics))

        if not all_items:
            selected_names = ", ".join(feed.display_name for feed in selected_feeds[:8])
            message = (
                f"Awin feed list was reachable and {len(selected_feeds)} feed(s) were checked, "
                "but no rows could be confirmed as discounted products. "
                "This does not mean the merchants have no products; it means the checked feed rows "
                "did not provide a usable old/current price pair or failed another import rule."
            )
            if selected_names:
                message += f" Checked feeds: {selected_names}."
            if diagnostics:
                message += " Diagnostics: " + "; ".join(diagnostics[:10])
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

        return all_items

    def _parse_options(self, provider_url: str) -> AwinFeedListOptions:
        settings = get_settings()
        parsed = urllib.parse.urlparse(provider_url)
        query = urllib.parse.parse_qs(parsed.query)

        return AwinFeedListOptions(
            max_feeds=self._bounded_int(query.get("max_feeds", [settings.awin_feed_max_feeds])[0], minimum=1, maximum=200),
            max_feeds_per_advertiser=self._bounded_int(
                query.get("max_feeds_per_advertiser", [settings.awin_feed_max_feeds_per_advertiser])[0],
                minimum=1,
                maximum=20,
            ),
            max_items_per_feed=self._bounded_int(
                query.get("max_items_per_feed", [settings.awin_feed_max_items_per_feed])[0],
                minimum=1,
                maximum=2000,
            ),
            max_scan_rows_per_feed=self._bounded_int(
                query.get("max_scan_rows_per_feed", query.get("max_scan_rows", [settings.awin_feed_max_scan_rows_per_feed]))[0],
                minimum=100,
                maximum=250000,
            ),
            min_discount_percent=self._bounded_int(
                query.get("min_discount_percent", query.get("min_discount", [settings.awin_feed_min_discount_percent]))[0],
                minimum=0,
                maximum=95,
            ),
            joined_only=self._bool_value(query.get("joined_only", ["true"])[0], default=True),
            advertiser_id=self._clean_query_value(query.get("advertiser_id", query.get("merchant_id", [""]))[0]),
            advertiser_name=self._clean_query_value(query.get("advertiser_name", query.get("merchant_name", [""]))[0]),
            excluded_advertiser_ids=self._parse_query_values(
                query.get("exclude_advertiser_ids", query.get("excluded_advertiser_ids", []))
            ),
        )

    def _parse_query_values(self, values: list[str]) -> tuple[str, ...]:
        parsed: list[str] = []
        seen: set[str] = set()
        for value in values:
            for part in re.split(r"[,;\s]+", str(value or "")):
                cleaned = part.strip().lower()
                if not cleaned or cleaned in seen:
                    continue
                seen.add(cleaned)
                parsed.append(cleaned)
        return tuple(parsed)

    def _clean_query_value(self, value: object) -> str:
        return str(value or "").strip()

    def _resolve_feed_list_url(self, provider_url: str) -> str:
        settings = get_settings()
        provider_url = provider_url.strip()
        if provider_url.startswith(("http://", "https://")):
            return provider_url

        if settings.awin_feed_list_url.strip():
            return settings.awin_feed_list_url.strip()

        api_key = settings.awin_datafeed_api_key.strip()
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="AWIN_DATAFEED_API_KEY or AWIN_FEED_LIST_URL must be configured before syncing Awin.",
            )

        return settings.awin_feed_list_endpoint_template.format(
            api_key=urllib.parse.quote(api_key),
            publisher_id=urllib.parse.quote(settings.awin_publisher_id.strip()),
        )

    def _select_feed_rows(self, rows: list[dict[str, Any]], *, options: AwinFeedListOptions) -> list["_AwinFeedRow"]:
        candidates: list[_AwinFeedRow] = []
        seen_urls: set[str] = set()

        for row in rows:
            raw_url = self._pick_url(row)
            if not raw_url or raw_url in seen_urls:
                continue

            if options.joined_only and not self._looks_joined_or_allowed(row):
                continue

            advertiser_name = self._pick_string(row, *self._ADVERTISER_KEYS) or "Awin advertiser"
            advertiser_id = self._pick_string(row, *self._ADVERTISER_ID_KEYS) or ""

            normalized_advertiser_id = advertiser_id.strip().lower()
            if options.advertiser_id and normalized_advertiser_id != options.advertiser_id.strip().lower():
                continue
            if options.advertiser_name and options.advertiser_name.strip().lower() not in advertiser_name.strip().lower():
                continue
            if normalized_advertiser_id and normalized_advertiser_id in options.excluded_advertiser_ids:
                continue

            seen_urls.add(raw_url)
            candidates.append(
                _AwinFeedRow(
                    feed_url=raw_url,
                    feed_name=self._pick_string(row, "feed_name", "feed", "name") or advertiser_name,
                    advertiser_name=advertiser_name,
                    advertiser_id=advertiser_id,
                    region=self._pick_string(row, *self._REGION_KEYS) or "",
                    language=self._pick_string(row, *self._LANGUAGE_KEYS) or "",
                )
            )

        if options.advertiser_id or options.advertiser_name:
            # Targeted providers intentionally inspect several feeds from one
            # merchant. Preserve Awin order and let max_feeds define the limit.
            return candidates[: options.max_feeds]

        # General provider: select feeds in advertiser round-robin order. The old
        # implementation selected one feed per merchant first and then filled the
        # remaining slots in raw Awin order. That still allowed one large merchant
        # to consume most spare slots and could leave TTfone/other stores stuck on
        # a non-productive first feed. Round-robin gives each advertiser feed #1,
        # then each advertiser feed #2, and so on up to the configured per-store cap.
        groups: dict[str, list[_AwinFeedRow]] = {}
        advertiser_order: list[str] = []
        for feed in candidates:
            advertiser_key = self._advertiser_key(feed)
            if advertiser_key not in groups:
                groups[advertiser_key] = []
                advertiser_order.append(advertiser_key)
            if len(groups[advertiser_key]) < options.max_feeds_per_advertiser:
                groups[advertiser_key].append(feed)

        selected: list[_AwinFeedRow] = []
        for feed_index in range(options.max_feeds_per_advertiser):
            added_in_round = False
            for advertiser_key in advertiser_order:
                advertiser_feeds = groups[advertiser_key]
                if feed_index >= len(advertiser_feeds):
                    continue
                selected.append(advertiser_feeds[feed_index])
                added_in_round = True
                if len(selected) >= options.max_feeds:
                    return selected
            if not added_in_round:
                break

        return selected

    def _advertiser_key(self, feed: "_AwinFeedRow") -> str:
        advertiser_id = feed.advertiser_id.strip().lower()
        if advertiser_id:
            return f"id:{advertiser_id}"
        advertiser_name = feed.advertiser_name.strip().lower()
        if advertiser_name and advertiser_name != "awin advertiser":
            return f"name:{advertiser_name}"
        return f"url:{feed.feed_url}"

    def _looks_joined_or_allowed(self, row: dict[str, Any]) -> bool:
        status_text = " ".join(
            str(row.get(key, "")).strip().lower()
            for key in self._STATUS_KEYS
            if row.get(key) not in (None, "")
        )
        if not status_text:
            # Some Awin feed-list variants already return only available feeds and
            # do not include relationship status. Do not block those rows.
            return True

        blocked = ("pending", "rejected", "declined", "suspended", "closed", "not joined", "not_joined")
        if any(value in status_text for value in blocked):
            return False

        allowed = ("joined", "approved", "active", "allowed", "accepted", "yes", "true")
        return any(value in status_text for value in allowed)

    def _prepare_feed_download_url(self, feed_url: str) -> str:
        settings = get_settings()
        api_key = settings.awin_datafeed_api_key.strip()
        publisher_id = settings.awin_publisher_id.strip()
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
        resolved = feed_url
        for placeholder, value in replacements.items():
            if value:
                resolved = resolved.replace(placeholder, urllib.parse.quote(value))
        return resolved

    def _is_blocked_awin_product(self, item: dict[str, Any]) -> bool:
        advertiser_id = self._pick_string(
            item,
            "_awin_advertiser_id",
            "advertiser_id",
            "merchant_id",
            "programme_id",
            "program_id",
        )
        normalized_advertiser_id = str(advertiser_id or "").strip()

        title = self._pick_string(
            item,
            "product_name",
            "productName",
            "productname",
            "aw_product_name",
            "name",
            "title",
        )
        normalized_title = re.sub(r"[^a-z0-9]+", " ", str(title or "").lower()).strip()
        for prefix in self._BLOCKED_TITLE_PREFIXES_BY_ADVERTISER.get(normalized_advertiser_id, ()):
            if normalized_title.startswith(prefix):
                return True

        product_id = self._pick_string(item, "aw_product_id", "merchant_product_id", "product_id", "sku", "id")
        if not normalized_advertiser_id or not product_id:
            return False
        return (normalized_advertiser_id, product_id.strip()) in self._BLOCKED_AWIN_PRODUCTS

    def _product_dedupe_key(self, item: dict[str, Any]) -> str:
        advertiser_id = self._pick_string(
            item,
            "_awin_advertiser_id",
            "advertiser_id",
            "merchant_id",
            "programme_id",
            "program_id",
        ) or ""
        product_id = self._pick_string(
            item,
            "aw_product_id",
            "merchant_product_id",
            "product_id",
            "sku",
            "id",
        ) or ""
        if advertiser_id and product_id:
            return f"product:{advertiser_id.strip().lower()}:{product_id.strip().lower()}"

        product_url = self._pick_string(
            item,
            "merchant_product_url",
            "merchant_deep_link",
            "product_url",
            "productUrl",
            "product_link",
            "link",
            "url",
        )
        if product_url:
            parsed = urllib.parse.urlsplit(product_url.strip())
            canonical_url = urllib.parse.urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/"), parsed.query, ""))
            return f"url:{canonical_url}"

        title = self._pick_string(item, "product_name", "productName", "productname", "aw_product_name", "name", "title") or ""
        image = self._pick_string(item, "merchant_image_url", "aw_image_url", "image_url", "image_link", "image") or ""
        current, old = self._awin_price_pair(item)
        return f"fallback:{advertiser_id.lower()}:{title.lower()}:{image}:{current}:{old}"

    def _filter_product_items(self, items: list[dict[str, Any]], *, min_discount_percent: int) -> list[dict[str, Any]]:
        filtered, _stats = self._filter_product_items_with_stats(items, min_discount_percent=min_discount_percent)
        return filtered

    def _filter_product_items_with_stats(
        self,
        items: list[dict[str, Any]],
        *,
        min_discount_percent: int,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        filtered: list[dict[str, Any]] = []
        stats = self._new_filter_stats()
        for item in items:
            if self._product_item_passes_rules(
                item,
                min_discount_percent=min_discount_percent,
                stats=stats,
            ):
                filtered.append(item)
        return filtered, stats

    def _new_filter_stats(self) -> dict[str, Any]:
        return {
            "rows": 0,
            "missing_title": 0,
            "missing_link": 0,
            "missing_image": 0,
            "missing_current_price": 0,
            "out_of_stock": 0,
            "no_discount_price_pair": 0,
            "below_min_discount": 0,
            "restricted_offer": 0,
            "passed": 0,
            "headers": [],
        }

    def _product_item_passes_rules(
        self,
        item: dict[str, Any],
        *,
        min_discount_percent: int,
        stats: dict[str, Any],
    ) -> bool:
        stats["rows"] = int(stats.get("rows", 0)) + 1
        if stats["rows"] <= 3:
            headers = {str(value) for value in stats.get("headers", [])}
            headers.update(str(key) for key in item.keys())
            stats["headers"] = sorted(headers)[:40]

        title = self._pick_string(item, "product_name", "productName", "productname", "aw_product_name", "name", "title")
        link = self._pick_string(
            item,
            "aw_deep_link",
            "deep_link",
            "deepLink",
            "deeplink",
            "affiliate_url",
            "tracking_url",
            "tracking_link",
            "merchant_deep_link",
            "merchant_product_url",
            "product_url",
            "productUrl",
            "product_link",
            "click_url",
            "clickout_url",
            "link",
            "url",
        )
        image = self._pick_string(
            item,
            "merchant_image_url",
            "aw_image_url",
            "aw_thumb_url",
            "large_image",
            "image_url",
            "image_link",
            "imageUrl",
            "thumbnail",
            "thumbnail_url",
            "merchant_thumb_url",
            "picture",
            "image",
        )
        current, old = self._awin_price_pair(item)

        if not title:
            stats["missing_title"] += 1
            return False
        if not link:
            stats["missing_link"] += 1
            return False
        if not image:
            stats["missing_image"] += 1
            return False
        if not current or current <= 0:
            stats["missing_current_price"] += 1
            return False
        if self._is_out_of_stock(item):
            stats["out_of_stock"] += 1
            return False

        if restricted_offer_match_for_mapping(
            item,
            keys=(
                "product_name",
                "productName",
                "productname",
                "aw_product_name",
                "name",
                "title",
                "description",
                "product_description",
                "product_short_description",
                "short_description",
                "merchant_product_description",
                "category_name",
                "merchant_category",
                "product_category",
                "category",
                "product_type",
                "merchant_product_url",
                "merchant_deep_link",
                "product_url",
                "productUrl",
                "url",
                "link",
            ),
        ):
            stats["restricted_offer"] += 1
            return False

        # DiscountHub must show real discounts only. Awin feeds may contain a
        # full product catalogue, so import only rows with a provable old/current
        # price pair. A reachable product page alone is not proof of a discount.
        if not old or old <= current:
            stats["no_discount_price_pair"] += 1
            return False
        discount = ((old - current) / old) * 100
        if discount <= 0 or discount < min_discount_percent:
            stats["below_min_discount"] += 1
            return False

        stats["passed"] += 1
        return True

    def _format_filter_stats(self, feed_row: "_AwinFeedRow", stats: dict[str, Any]) -> str:
        headers = stats.get("headers") or []
        headers_text = ", ".join(str(value) for value in headers[:18])
        return (
            f"{feed_row.display_name}: rows={stats.get('rows', 0)}, passed={stats.get('passed', 0)}, "
            f"returned={stats.get('returned', stats.get('passed', 0))}, "
            f"missing_title={stats.get('missing_title', 0)}, missing_link={stats.get('missing_link', 0)}, "
            f"missing_image={stats.get('missing_image', 0)}, missing_current_price={stats.get('missing_current_price', 0)}, "
            f"no_discount_price_pair={stats.get('no_discount_price_pair', 0)}, "
            f"below_min_discount={stats.get('below_min_discount', 0)}, restricted_offer={stats.get('restricted_offer', 0)}, "
            f"out_of_stock={stats.get('out_of_stock', 0)}, "
            f"headers=[{headers_text}]"
        )

    def _awin_price_pair(self, item: dict[str, Any]) -> tuple[float | None, float | None]:
        # Awin feeds can be in native Awin format or Google Merchant format.
        # In Google format, `price` is the normal/original price and `sale_price`
        # is the discounted price. Awin native feeds may also expose
        # `product_price_old`, `saving`, or `savings_percent`; derive old price
        # from those fields when there is no explicit old/RRP price column.
        sale_price = self._pick_number(
            item,
            "sale_price",
            "saleprice",
            "discount_price",
            "discounted_price",
            "offer_price",
            "special_price",
            "promo_price",
            "promotional_price",
            "final_price",
            "reduced_price",
            "price_sale",
            "saleprice_value",
            "now_price",
            "current_price",
            "currentprice",
            "price_current",
            "merchant_product_price",
        )
        listed_price = self._pick_number(
            item,
            "product_price",
            "search_price",
            "store_price",
            "price",
            "base_price",
            "full_price",
            "normal_price",
            "normalprice",
            "amount",
            "price_value",
        )
        old_price = self._pick_number(
            item,
            "product_price_old",
            "productpriceold",
            "rrp_price",
            "rrp",
            "old_price",
            "oldprice",
            "was_price",
            "wasprice",
            "list_price",
            "listprice",
            "original_price",
            "originalprice",
            "retail_price",
            "retailprice",
            "regular_price",
            "regularprice",
            "previous_price",
            "previousprice",
            "before_price",
            "strikethrough_price",
            "compare_at_price",
            "compare_price",
            "msrp",
            "recommended_retail_price",
            "merchant_product_price_old",
            "product_price_rrp",
            "price_old",
            "price_was",
        )
        saving_amount = self._pick_number(
            item,
            "saving",
            "savings",
            "saving_amount",
            "savings_amount",
            "discount_amount",
            "amount_saved",
        )
        saving_percent = self._pick_number(
            item,
            "savings_percent",
            "saving_percent",
            "discount_percent",
            "discount_percentage",
            "percentage_discount",
            "percent_discount",
        )

        if sale_price and sale_price > 0:
            current = sale_price
            old = old_price
            if old and old > current:
                return current, old
            if listed_price and listed_price > current:
                return current, listed_price
            derived_old = self._derive_old_price(current=current, saving_amount=saving_amount, saving_percent=saving_percent)
            return current, derived_old or old or listed_price

        current = listed_price
        if current and current > 0 and (not old_price or old_price <= current):
            derived_old = self._derive_old_price(current=current, saving_amount=saving_amount, saving_percent=saving_percent)
            if derived_old and derived_old > current:
                return current, derived_old
        return current, old_price

    def _derive_old_price(
        self,
        *,
        current: float | None,
        saving_amount: float | None,
        saving_percent: float | None,
    ) -> float | None:
        if not current or current <= 0:
            return None
        if saving_amount and saving_amount > 0:
            return current + saving_amount
        if saving_percent and 0 < saving_percent < 100:
            return current / (1 - (saving_percent / 100))
        return None

    def _is_out_of_stock(self, item: dict[str, Any]) -> bool:
        bad_markers = (
            "out of stock",
            "out_of_stock",
            "sold out",
            "sold_out",
            "unavailable",
            "not available",
            "not_available",
            "discontinued",
            "ended",
            "expired",
        )
        boolean_keys = ("in_stock", "instock", "is_available", "available")
        status_keys = ("stock_status", "availability", "availability_status", "g_availability", "g:availability", "stock")
        quantity_keys = ("stock_quantity", "inventory_quantity", "quantity", "qty")

        for key in boolean_keys:
            value = self._pick_string(item, key)
            if value is None:
                continue
            text = value.strip().lower()
            if text in {"0", "0.0", "false", "no", "n", "off"}:
                return True
            if any(marker in text for marker in bad_markers):
                return True

        for key in status_keys:
            value = self._pick_string(item, key)
            if value is None:
                continue
            text = value.strip().lower()
            if any(marker in text for marker in bad_markers):
                return True

        for key in quantity_keys:
            value = self._pick_number(item, key)
            if value is not None and value <= 0:
                return True

        return False

    def _fetch_text(self, feed_url: str, *, timeout_seconds: int) -> tuple[str, str]:
        try:
            request = urllib.request.Request(
                feed_url,
                headers={
                    "Accept": "application/json,text/csv,text/tab-separated-values,*/*",
                    "User-Agent": "DiscountHub-Awin-Importer/0.1",
                },
            )
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                content_type = response.headers.get("content-type", "") or ""
                content_encoding = (response.headers.get("content-encoding", "") or "").lower()
                charset = response.headers.get_content_charset() or "utf-8"
                raw_bytes = response.read()
        except urllib.error.URLError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not fetch Awin URL: {exc}",
            ) from exc

        if content_encoding == "gzip" or raw_bytes.startswith(b"\x1f\x8b") or feed_url.lower().split("?")[0].endswith(".gz"):
            try:
                raw_bytes = gzip.decompress(raw_bytes)
            except OSError as exc:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not decompress Awin gzip feed: {exc}") from exc

        return raw_bytes.decode(charset, errors="replace"), content_type.lower()

    def _fetch_filtered_product_items(
        self,
        feed_url: str,
        *,
        timeout_seconds: int,
        max_items: int,
        max_scan_rows: int,
        min_discount_percent: int,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Scan deeply enough to find deals instead of judging only the first rows.

        Awin feeds are often ordered by category, SKU, or creation date. Reading only
        the first ``max_items`` physical rows caused valid stores to appear empty when
        their discounted products were later in the same feed. This method scans up to
        ``max_scan_rows`` rows and returns at most ``max_items`` confirmed discounts.
        """
        try:
            request = urllib.request.Request(
                feed_url,
                headers={
                    "Accept": "text/csv,text/tab-separated-values,application/json,*/*",
                    "User-Agent": "DiscountHub-Awin-Importer/0.2",
                },
            )
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                content_type = (response.headers.get("content-type", "") or "").lower()
                content_encoding = (response.headers.get("content-encoding", "") or "").lower()
                charset = response.headers.get_content_charset() or "utf-8"
                path = feed_url.lower().split("?")[0]

                raw_stream: Any = response
                is_gzip = "gzip" in content_encoding or path.endswith(".gz")
                if not is_gzip and hasattr(response, "peek"):
                    try:
                        is_gzip = response.peek(2).startswith(b"\x1f\x8b")
                    except (AttributeError, OSError):
                        is_gzip = False
                if is_gzip:
                    raw_stream = gzip.GzipFile(fileobj=response)

                is_json = "json" in content_type or path.endswith(".json") or path.endswith(".json.gz")
                if is_json:
                    raw_body = raw_stream.read(25 * 1024 * 1024 + 1)
                    if len(raw_body) > 25 * 1024 * 1024:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Awin JSON product feed is larger than the 25 MB safety cap.",
                        )
                    items = self._extract_items_from_body(
                        raw_body.decode(charset, errors="replace"),
                        feed_url=feed_url,
                        content_type=content_type,
                    )[:max_scan_rows]
                else:
                    text_stream = io.TextIOWrapper(raw_stream, encoding=charset, errors="replace", newline="")
                    return self._extract_filtered_delimited_stream(
                        text_stream,
                        feed_url=feed_url,
                        content_type=content_type,
                        max_items=max_items,
                        max_scan_rows=max_scan_rows,
                        min_discount_percent=min_discount_percent,
                    )

        except HTTPException:
            raise
        except (urllib.error.URLError, OSError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not fetch Awin product feed: {exc}",
            ) from exc

        filtered, stats = self._filter_product_items_with_stats(
            items,
            min_discount_percent=min_discount_percent,
        )
        stats["scanned_rows"] = stats.get("rows", 0)
        stats["scan_limit"] = max_scan_rows
        stats["returned"] = min(len(filtered), max_items)
        return filtered[:max_items], stats

    def _extract_filtered_delimited_stream(
        self,
        stream: io.TextIOBase,
        *,
        feed_url: str,
        content_type: str,
        max_items: int,
        max_scan_rows: int,
        min_discount_percent: int,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        sample_lines: list[str] = []
        for _ in range(25):
            line = stream.readline()
            if line == "":
                break
            sample_lines.append(line)
        if not sample_lines:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Awin product feed was empty.")

        sample = "".join(sample_lines)
        path = feed_url.lower().split("?")[0]
        delimiter = "\t" if path.endswith((".tsv", ".tsv.gz")) or "tab-separated" in content_type else None
        if delimiter is None:
            try:
                delimiter = csv.Sniffer().sniff(sample[:8192], delimiters=",;\t|").delimiter
            except csv.Error:
                delimiter = ","

        reader = csv.DictReader(itertools.chain(sample_lines, stream), delimiter=delimiter)
        if not reader.fieldnames:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Awin feed must have a header row.")

        headers = [str(header or "").strip() for header in reader.fieldnames]
        filtered: list[dict[str, Any]] = []
        stats = self._new_filter_stats()
        for row_index, row in enumerate(reader, start=1):
            if row_index > max_scan_rows:
                break
            item = self._csv_row_to_item(row=row, headers=headers)
            if not item:
                continue
            if self._product_item_passes_rules(
                item,
                min_discount_percent=min_discount_percent,
                stats=stats,
            ):
                filtered.append(item)
                if len(filtered) >= max_items:
                    break

        stats["scanned_rows"] = stats.get("rows", 0)
        stats["scan_limit"] = max_scan_rows
        stats["returned"] = len(filtered)
        return filtered, stats

    def _csv_row_to_item(self, *, row: dict[str, Any], headers: list[str]) -> dict[str, Any]:
        item: dict[str, Any] = {}
        for raw_key, value in row.items():
            key = str(raw_key or "").strip()
            if not key:
                continue
            item[key] = value.strip() if isinstance(value, str) else value

        for header in headers:
            if not header or header not in item:
                continue
            normalized_key = self._normalize_header(header)
            item.setdefault(normalized_key, item[header])

        if any(value not in (None, "") for value in item.values()):
            return item
        return {}

    def _extract_items_from_body(self, raw_body: str, *, feed_url: str, content_type: str) -> list[dict[str, Any]]:
        stripped = raw_body.lstrip("\ufeff\n\r\t ")
        looks_like_json = stripped.startswith(("[", "{")) or "json" in content_type
        looks_like_tsv = feed_url.lower().split("?")[0].endswith(".tsv") or "tab-separated" in content_type

        if looks_like_json:
            try:
                raw_data = json.loads(raw_body)
                return self._extract_json_items(raw_data)
            except json.JSONDecodeError as exc:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Awin feed did not return valid JSON: {exc}") from exc

        delimiter = "\t" if looks_like_tsv else None
        return self._extract_csv_items(raw_body, delimiter=delimiter)

    def _extract_json_items(self, raw_data: Any) -> list[dict[str, Any]]:
        if isinstance(raw_data, list):
            return [item for item in raw_data if isinstance(item, dict)]
        if isinstance(raw_data, dict):
            for key in ("feeds", "items", "products", "data", "results"):
                value = raw_data.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Awin JSON feed did not contain a supported array.")

    def _extract_csv_items(self, raw_body: str, *, delimiter: str | None = None) -> list[dict[str, Any]]:
        sample = raw_body[:8192]
        if delimiter is None:
            try:
                delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
            except csv.Error:
                delimiter = ","

        reader = csv.DictReader(io.StringIO(raw_body), delimiter=delimiter)
        if not reader.fieldnames:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Awin feed must have a header row.")

        headers = [str(header or "").strip() for header in reader.fieldnames]
        items: list[dict[str, Any]] = []
        for row in reader:
            item: dict[str, Any] = {}
            for raw_key, value in row.items():
                key = str(raw_key or "").strip()
                if not key:
                    continue
                item[key] = value.strip() if isinstance(value, str) else value

            for header in headers:
                if not header or header not in item:
                    continue
                normalized_key = self._normalize_header(header)
                item.setdefault(normalized_key, item[header])

            if any(value not in (None, "") for value in item.values()):
                items.append(item)
        return items

    def _pick_url(self, row: dict[str, Any]) -> str | None:
        # First try known headers, then scan all string values. Feed-list exports
        # often localize/rename the URL column over time.
        direct = self._pick_string(row, *self._FEED_URL_KEYS)
        if direct and direct.startswith(("http://", "https://")):
            return direct

        for value in row.values():
            text = str(value or "").strip()
            if text.startswith(("http://", "https://")) and ("product" in text.lower() or "feed" in text.lower() or "download" in text.lower()):
                return text
        return None

    def _pick_string(self, item: dict[str, Any], *keys: str) -> str | None:
        for key in keys:
            for candidate in (key, self._normalize_header(key)):
                value = item.get(candidate)
                if value is None:
                    continue
                text = str(value).strip()
                if text:
                    return text
        return None

    def _pick_number(self, item: dict[str, Any], *keys: str) -> float | None:
        for key in keys:
            value = self._pick_string(item, key)
            if value is None or value == "":
                continue
            parsed = self._parse_number_text(value)
            if parsed is not None:
                return parsed
        return None

    def _parse_number_text(self, value: object) -> float | None:
        if isinstance(value, int | float):
            return float(value)
        text = str(value or "").strip().replace("\u00a0", " ")
        match = re.search(r"[-+]?\d[\d\s.,'’]*", text)
        if not match:
            return None
        token = match.group(0).replace(" ", "").replace("'", "").replace("’", "")
        sign = ""
        if token[:1] in {"+", "-"}:
            sign, token = token[0], token[1:]
        if not token:
            return None

        if "," in token and "." in token:
            decimal_separator = "," if token.rfind(",") > token.rfind(".") else "."
            thousands_separator = "." if decimal_separator == "," else ","
            token = token.replace(thousands_separator, "")
            token = token.replace(decimal_separator, ".")
        elif "," in token or "." in token:
            separator = "," if "," in token else "."
            parts = token.split(separator)
            if len(parts) > 2:
                last = parts[-1]
                token = "".join(parts[:-1]) + ("." + last if 1 <= len(last) <= 2 else last)
            else:
                before, after = parts
                if len(after) == 3 and before:
                    token = before + after
                else:
                    token = before + "." + after

        try:
            return float(sign + token)
        except ValueError:
            return None

    def _bounded_int(self, value: Any, *, minimum: int, maximum: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = minimum
        return max(minimum, min(maximum, parsed))

    def _bool_value(self, value: Any, *, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        text = str(value or "").strip().lower()
        if text in {"1", "true", "yes", "y", "on"}:
            return True
        if text in {"0", "false", "no", "n", "off"}:
            return False
        return default

    def _normalize_header(self, value: str) -> str:
        normalized = value.strip().replace("/", "_").replace("-", "_")
        normalized = "".join(char if char.isalnum() else "_" for char in normalized)
        while "__" in normalized:
            normalized = normalized.replace("__", "_")
        return normalized.strip("_").lower()


@dataclass(frozen=True)
class _AwinFeedRow:
    feed_url: str
    feed_name: str
    advertiser_name: str
    advertiser_id: str
    region: str
    language: str

    @property
    def display_name(self) -> str:
        if self.advertiser_id:
            return f"{self.advertiser_name} ({self.advertiser_id})"
        return self.advertiser_name


awin_feed_list_service = AwinFeedListService()
