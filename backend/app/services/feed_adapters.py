from __future__ import annotations

import hashlib
import html
import re
import urllib.parse
from datetime import datetime, timezone
from typing import Any

from app.services.admitad_deeplink_service import admitad_deeplink_service
from app.services.country_availability import normalize_availability

from fastapi import HTTPException, status

from app.models.deal import DealUpsertRequest
from app.models.feed_provider import FeedProviderAdapter


class FeedAdapterService:
    """Normalizes different partner feed formats into DiscountHub deals.

    This is the layer that lets DiscountHub work automatically with multiple
    providers without manually adding products one by one.
    """

    def normalize_items(
        self,
        *,
        adapter: FeedProviderAdapter,
        raw_items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        selected = self._detect_adapter(adapter, raw_items)

        if selected == "discounthub_json":
            return [self._normalize_discounthub(item) for item in raw_items]
        if selected in {"generic_products", "csv_products"}:
            return [self._normalize_generic(item) for item in raw_items]
        if selected == "google_merchant":
            return [self._normalize_google_merchant(item) for item in raw_items]
        if selected == "awin_products":
            return [self._normalize_awin(item) for item in raw_items]
        if selected == "admitad_products":
            return [self._normalize_admitad(item) for item in raw_items]
        if selected == "rakuten_products":
            return [self._normalize_rakuten(item) for item in raw_items]
        if selected == "cj_products":
            return [self._normalize_cj(item) for item in raw_items]
        if selected == "impact_products":
            return [self._normalize_impact(item) for item in raw_items]
        if selected == "ebay_browse_api":
            return [self._normalize_ebay_browse(item) for item in raw_items]
        if selected == "mercadolibre_search_api":
            return [self._normalize_mercadolibre(item) for item in raw_items]

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported feed adapter: {adapter}",
        )

    def _detect_adapter(self, adapter: FeedProviderAdapter, raw_items: list[dict[str, Any]]) -> FeedProviderAdapter:
        if adapter != "auto":
            return adapter

        first = raw_items[0] if raw_items else {}
        keys = set(first.keys())

        if {"title", "oldPrice", "currentPrice", "productUrl"}.issubset(keys):
            return "discounthub_json"
        if {"title", "old_price", "current_price", "product_url"}.issubset(keys):
            return "discounthub_json"
        if {"image_link", "sale_price", "price", "link"}.issubset(keys):
            return "google_merchant"
        if {"product_name", "merchant_name", "deep_link"}.issubset(keys):
            return "awin_products"
        if {"name", "gotolink", "picture"}.issubset(keys) or {"name", "deeplink", "picture"}.issubset(keys):
            return "admitad_products"
        if {"productname", "advertisername", "buyurl"}.issubset(keys):
            return "rakuten_products"
        if {"advertiser_name", "buy_url", "image_url"}.issubset(keys):
            return "cj_products"
        if {"AdvertiserName", "TrackingUrl", "ImageUrl"}.issubset(keys) or {"advertisername", "trackingurl", "imageurl"}.issubset(keys):
            return "impact_products"
        if {"itemId", "itemWebUrl", "price"}.issubset(keys):
            return "ebay_browse_api"
        if {"id", "permalink", "price", "currency_id"}.issubset(keys):
            return "mercadolibre_search_api"
        return "generic_products"

    def _normalize_discounthub(self, item: dict[str, Any]) -> dict[str, Any]:
        # Already close to our API contract. DealUpsertRequest accepts camelCase
        # and snake_case aliases, so we only fill missing safety defaults.
        normalized = dict(item)
        normalized.setdefault("id", self._stable_id(normalized, prefix="feed"))
        normalized.setdefault("description", normalized.get("title", "Discounted product"))
        normalized.setdefault("platform", normalized.get("merchant") or normalized.get("store") or "Feed")
        normalized.setdefault("category", "Other")
        normalized.setdefault("currency", "USD")
        normalized.setdefault("rating", 0)
        normalized.setdefault("reviewCount", normalized.get("review_count", 0))
        normalized.setdefault("freeShipping", normalized.get("free_shipping", False))
        normalized.setdefault("verified", normalized.get("verified", False))
        normalized.setdefault("shipsTo", normalized.get("ships_to", []))
        normalized.setdefault("hotDeal", normalized.get("hot_deal", False))
        normalized.setdefault("lowestPrice", normalized.get("lowest_price", False))
        return normalized

    def _normalize_generic(self, item: dict[str, Any]) -> dict[str, Any]:
        product_url = self._pick_string(item, "productUrl", "product_url", "url", "link", "product_link", "deeplink", "deep_link", "buy_url", "buyurl", "producturl")
        title = self._pick_string(item, "title", "name", "product_name", "productName", "productname")
        platform = self._pick_string(item, "platform", "merchant", "merchant_name", "store", "shop", "advertiser_name", "advertisername", "advertiser") or "Feed"

        return {
            "id": self._pick_string(item, "id", "sku", "product_id", "productId") or self._stable_id(item, prefix="generic"),
            "title": title or "Untitled product",
            "description": self._pick_string(item, "description", "summary", "short_description") or title or "Discounted product",
            "imageUrl": self._pick_string(item, "imageUrl", "image_url", "image", "image_link", "thumbnail", "imageurl", "picture", "large_image") or "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=1200",
            "platform": platform,
            "category": self._pick_string(item, "category", "category_name", "categoryName", "product_type") or "Other",
            "oldPrice": self._pick_number(item, "oldPrice", "old_price", "list_price", "regular_price", "price_before_discount", "was_price", "rrp") or 1,
            "currentPrice": self._pick_number(item, "currentPrice", "current_price", "sale_price", "price", "offer_price", "now_price") or 1,
            "currency": self._pick_currency(item) or "USD",
            "productUrl": product_url or "https://example.com/",
            "affiliateUrl": self._pick_string(item, "affiliateUrl", "affiliate_url", "tracking_url", "trackingurl", "deeplink", "deep_link", "go_to_link", "gotolink", "buy_url", "buyurl") or product_url,
            "rating": self._pick_number(item, "rating", "average_rating", "review_rating") or 0,
            "reviewCount": int(self._pick_number(item, "reviewCount", "review_count", "reviews", "rating_count") or 0),
            "freeShipping": self._pick_bool(item, "freeShipping", "free_shipping", "shipping_free", "free_delivery"),
            "verified": self._pick_bool(item, "verified", "is_verified", default=True),
            "shipsTo": self._pick_list(item, "shipsTo", "ships_to", "countries", "shipping_countries"),
            "hotDeal": self._pick_bool(item, "hotDeal", "hot_deal", "is_hot", "featured"),
            "lowestPrice": self._pick_bool(item, "lowestPrice", "lowest_price", "best_price"),
        }

    def _normalize_google_merchant(self, item: dict[str, Any]) -> dict[str, Any]:
        title = self._pick_string(item, "title") or "Untitled product"
        link = self._pick_string(item, "link", "mobile_link") or "https://example.com/"
        sale_price = self._pick_number(item, "sale_price", "salePrice")
        price = self._pick_number(item, "price")
        current = sale_price or price or 1
        old = price if sale_price and price and price > sale_price else current

        return {
            "id": self._pick_string(item, "id", "offer_id") or self._stable_id(item, prefix="google"),
            "title": title,
            "description": self._pick_string(item, "description") or title,
            "imageUrl": self._pick_string(item, "image_link", "additional_image_link") or "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=1200",
            "platform": self._pick_string(item, "brand", "store", "merchant") or "GoogleMerchantFeed",
            "category": self._pick_string(item, "product_type", "google_product_category") or "Other",
            "oldPrice": old,
            "currentPrice": current,
            "currency": self._pick_currency(item) or "USD",
            "productUrl": link,
            "affiliateUrl": self._pick_string(item, "ads_redirect", "tracking_url") or link,
            "rating": self._pick_number(item, "rating") or 0,
            "reviewCount": int(self._pick_number(item, "review_count") or 0),
            "freeShipping": self._pick_bool(item, "free_shipping", "freeShipping"),
            "verified": True,
            "shipsTo": self._pick_list(item, "shipping_country", "ships_to", "countries"),
            "hotDeal": True if old > current and ((old - current) / old) >= 0.3 else False,
            "lowestPrice": self._pick_bool(item, "lowest_price", "lowestPrice"),
        }

    def _normalize_awin(self, item: dict[str, Any]) -> dict[str, Any]:
        title = self._clean_text(
            self._pick_string(
                item,
                "product_name",
                "productName",
                "name",
                "title",
                "aw_product_name",
                "productname",
            ) or "Untitled Awin product"
        )
        deep_link = self._pick_string(
            item,
            "aw_deep_link",
            "deep_link",
            "deepLink",
            "deeplink",
            "affiliate_url",
            "tracking_url",
            "product_url",
            "productUrl",
            "merchant_deep_link",
            "merchant_product_url",
            "product_link",
            "click_url",
            "clickout_url",
            "link",
            "url",
        ) or "https://example.com/"
        merchant_product_url = self._pick_string(
            item,
            "merchant_product_url",
            "merchant_deep_link",
            "product_url",
            "url",
            "productUrl",
            "product_link",
            "link",
        ) or deep_link
        current, old = self._awin_price_pair(item)
        current = current or 1
        old = old or current
        image_url = self._pick_string(
            item,
            "merchant_image_url",
            "aw_image_url",
            "image_url",
            "large_image",
            "merchant_thumb_url",
            "aw_thumb_url",
            "thumbnail",
            "thumbnail_url",
            "image_link",
            "imageUrl",
            "picture",
            "image",
        ) or "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=1200"
        platform = self._clean_text(
            self._pick_string(
                item,
                "_awin_advertiser_name",
                "advertiser_name",
                "merchant_name",
                "programme_name",
                "program_name",
                "shop",
                "store",
            ) or "Awin Merchant"
        )
        raw_category = self._pick_string(
            item,
            "category_name",
            "merchant_category",
            "product_category",
            "category",
            "product_type",
        )
        category = self._clean_text(raw_category) if raw_category else self._infer_awin_category(title=title, platform=platform)
        brand = self._clean_text(self._pick_string(item, "brand_name", "brand", "manufacturer") or "")
        description = self._clean_text(
            self._pick_string(
                item,
                "description",
                "product_description",
                "product_short_description",
                "short_description",
                "merchant_product_description",
            ) or title
        )
        if brand and brand.lower() not in description.lower():
            description = f"{brand} · {description}"

        merchant_id = self._pick_string(item, "_awin_advertiser_id", "advertiser_id", "merchant_id", "programme_id", "program_id") or platform
        external_id = self._pick_string(item, "aw_product_id", "merchant_product_id", "product_id", "sku", "id") or self._stable_id(item, prefix="awin")
        item_id = self._safe_key(f"{merchant_id}_{external_id}") or self._stable_id(item, prefix="awin")
        discount = ((old - current) / old) if old > 0 else 0
        availability_countries, is_global = normalize_availability(
            self._pick_list(
                item,
                "availability_countries",
                "country_codes",
                "region_codes",
                "_awin_feed_region",
            )
        )
        if is_global:
            availability_countries = []

        return {
            "id": f"awin_{item_id}",
            "title": title,
            "description": description,
            "imageUrl": image_url,
            "platform": platform,
            "category": category,
            "oldPrice": round(old, 2),
            "currentPrice": round(current, 2),
            "currency": self._pick_currency(item) or self._infer_awin_currency(item),
            "productUrl": merchant_product_url,
            "affiliateUrl": deep_link,
            "rating": self._pick_number(item, "average_rating", "rating") or 0,
            "reviewCount": int(self._pick_number(item, "review_count", "reviews") or 0),
            "freeShipping": self._pick_bool(item, "free_shipping", "free_delivery", "delivery_free"),
            "verified": True,
            "shipsTo": self._pick_list(item, "ships_to", "shipping_countries"),
            "availabilityCountries": availability_countries,
            "isGlobal": is_global,
            "hotDeal": discount >= 0.3,
            "lowestPrice": self._pick_bool(item, "lowest_price", "lowestPrice", "best_price"),
        }

    def _awin_price_pair(self, item: dict[str, Any]) -> tuple[float | None, float | None]:
        # Awin feeds can be native Awin feeds or Google Merchant feeds. In Google
        # format `sale_price` is the discounted price while `price` is the normal
        # price. Awin native feeds may also provide `product_price_old`, `saving`,
        # or `savings_percent`; derive the old price from those fields where possible.
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
            if old_price and old_price > current:
                return current, old_price
            if listed_price and listed_price > current:
                return current, listed_price
            derived_old = self._derive_old_price(current=current, saving_amount=saving_amount, saving_percent=saving_percent)
            return current, derived_old or old_price or listed_price

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

    def _infer_awin_category(self, *, title: str, platform: str) -> str:
        text = f" {title} {platform} ".lower()
        if any(value in text for value in ("laptop", "macbook", "computer", "pc ", "memory", "ssd", "proshop", "apple")):
            return "Computers"
        if any(value in text for value in ("phone", "smartwatch", "headphone", "camera", "electronics", "charger", "speaker")):
            return "Electronics"
        if any(value in text for value in ("shoe", "sneaker", "dress", "shirt", "jacket", "fashion", "zalando", "nelly", "foot locker", "calvin klein")):
            return "Fashion"
        if any(value in text for value in ("kitchen", "home", "vacuum", "bosch", "kitchenaid", "sharkninja", "furniture", "garden")):
            return "Home"
        if any(value in text for value in ("fitness", "sport", "bike", "outdoor", "decathlon", "snowboard")):
            return "Sports"
        if any(value in text for value in ("clinique", "beauty", "makeup", "cosmetic", "perfume", "lookfantastic", "douglas")):
            return "Beauty"
        if any(value in text for value in ("lego", "toy", "game")):
            return "Toys"
        return "Other"

    def _normalize_admitad(self, item: dict[str, Any]) -> dict[str, Any]:
        title = self._pick_string(item, "name", "title", "product_name", "productname") or "Untitled Admitad product"
        raw_product_url = self._pick_string(
            item,
            "url",
            "product_url",
            "productUrl",
            "producturl",
            "link",
            "product_link",
            "productLink",
            "merchant_product_url",
            "merchant_deep_link",
            "target_url",
            "dl_target_url",
            "landing_page",
        )
        raw_affiliate_url = (
            self._pick_string(
                item,
                "gotolink",
                "goto_link",
                "go_to_link",
                "deeplink",
                "deep_link",
                "tracking_url",
                "affiliate_url",
            )
            or raw_product_url
            or "https://www.admitad.com/"
        )

        # Admitad product feeds can put a default tracking link in `gotolink`
        # and the real product page in a separate URL column. Build a generic
        # product deeplink only for Admitad here; eBay/Awin paths are untouched.
        product_url = (
            admitad_deeplink_service.extract_target_url(raw_product_url)
            or admitad_deeplink_service.extract_target_url(raw_affiliate_url)
            or raw_product_url
        )
        affiliate_url = (
            admitad_deeplink_service.build_manual_deeplink(raw_affiliate_url, product_url)
            or product_url
            or raw_affiliate_url
        )
        current = self._pick_number(item, "price", "sale_price", "current_price", "product_price", "search_price") or 1
        old = self._pick_number(item, "oldprice", "old_price", "original_price", "rrp", "retail_price", "was_price") or current
        raw_id = self._pick_string(item, "id", "product_id", "productid", "sku") or self._stable_id(item, prefix="admitad")
        safe_id = raw_id if raw_id.startswith("admitad_") else f"admitad_{self._safe_key(raw_id)}"
        platform = self._pick_string(
            item,
            "_discounthub_platform_name",
            "platform_name",
            "shop",
            "merchant",
            "merchant_name",
            "vendor",
            "campaign_name",
        ) or "Admitad Merchant"
        category = self._pick_string(item, "category", "category_name", "categoryname") or self._infer_awin_category(title=title, platform=platform)

        return {
            "id": safe_id,
            "title": title,
            "description": self._pick_string(item, "description", "short_description") or title,
            "imageUrl": self._pick_string(item, "picture", "image", "image_url", "imageurl") or "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=1200",
            "platform": platform,
            "category": category,
            "oldPrice": old,
            "currentPrice": current,
            "currency": self._pick_currency(item) or "USD",
            "productUrl": product_url or affiliate_url,
            "affiliateUrl": affiliate_url,
            "rating": self._pick_number(item, "rating", "average_rating") or 0,
            "reviewCount": int(self._pick_number(item, "review_count", "reviews") or 0),
            "freeShipping": self._pick_bool(item, "free_shipping", "free_delivery", "shipping_free"),
            "verified": True,
            "shipsTo": self._pick_list(item, "ships_to", "countries", "shipping_countries"),
            "hotDeal": True if old > current and ((old - current) / old) >= 0.3 else False,
            "lowestPrice": self._pick_bool(item, "lowest_price", "best_price"),
        }

    def _normalize_rakuten(self, item: dict[str, Any]) -> dict[str, Any]:
        title = self._pick_string(item, "productname", "product_name", "name", "title") or "Untitled Rakuten product"
        product_url = self._pick_string(item, "producturl", "product_url", "url", "link")
        affiliate_url = self._pick_string(item, "buyurl", "buy_url", "tracking_url", "deeplink") or product_url or "https://rakutenadvertising.com/"
        current = self._pick_number(item, "price", "saleprice", "sale_price", "current_price") or 1
        old = self._pick_number(item, "retailprice", "retail_price", "old_price", "rrp") or current

        return {
            "id": self._pick_string(item, "sku", "productid", "product_id", "id") or self._stable_id(item, prefix="rakuten"),
            "title": title,
            "description": self._pick_string(item, "description", "shortdescription", "short_description") or title,
            "imageUrl": self._pick_string(item, "imageurl", "image_url", "image", "thumbnail") or "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=1200",
            "platform": self._pick_string(item, "advertisername", "advertiser_name", "merchant", "merchant_name") or "Rakuten Merchant",
            "category": self._pick_string(item, "category", "categoryname", "category_name") or "Other",
            "oldPrice": old,
            "currentPrice": current,
            "currency": self._pick_currency(item) or "USD",
            "productUrl": product_url or affiliate_url,
            "affiliateUrl": affiliate_url,
            "rating": self._pick_number(item, "rating", "average_rating") or 0,
            "reviewCount": int(self._pick_number(item, "review_count", "reviews") or 0),
            "freeShipping": self._pick_bool(item, "free_shipping", "free_delivery", "shipping_free"),
            "verified": True,
            "shipsTo": self._pick_list(item, "ships_to", "countries", "shipping_countries"),
            "hotDeal": True if old > current and ((old - current) / old) >= 0.3 else False,
            "lowestPrice": self._pick_bool(item, "lowest_price", "best_price"),
        }

    def _normalize_cj(self, item: dict[str, Any]) -> dict[str, Any]:
        title = self._pick_string(item, "title", "name", "product_name", "productname") or "Untitled CJ product"
        product_url = self._pick_string(item, "product_url", "producturl", "url", "link")
        affiliate_url = self._pick_string(item, "buy_url", "buyurl", "tracking_url", "deeplink", "deep_link") or product_url or "https://cj.com/"
        current = self._pick_number(item, "sale_price", "saleprice", "price", "current_price") or 1
        old = self._pick_number(item, "retail_price", "retailprice", "old_price", "was_price") or current

        return {
            "id": self._pick_string(item, "sku", "product_id", "productid", "id") or self._stable_id(item, prefix="cj"),
            "title": title,
            "description": self._pick_string(item, "description", "short_description") or title,
            "imageUrl": self._pick_string(item, "image_url", "imageurl", "image", "thumbnail") or "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=1200",
            "platform": self._pick_string(item, "advertiser_name", "advertisername", "merchant", "merchant_name") or "CJ Merchant",
            "category": self._pick_string(item, "category", "category_name", "categoryname") or "Other",
            "oldPrice": old,
            "currentPrice": current,
            "currency": self._pick_currency(item) or "USD",
            "productUrl": product_url or affiliate_url,
            "affiliateUrl": affiliate_url,
            "rating": self._pick_number(item, "rating", "average_rating") or 0,
            "reviewCount": int(self._pick_number(item, "review_count", "reviews") or 0),
            "freeShipping": self._pick_bool(item, "free_shipping", "free_delivery", "shipping_free"),
            "verified": True,
            "shipsTo": self._pick_list(item, "ships_to", "countries", "shipping_countries"),
            "hotDeal": True if old > current and ((old - current) / old) >= 0.3 else False,
            "lowestPrice": self._pick_bool(item, "lowest_price", "best_price"),
        }

    def _normalize_impact(self, item: dict[str, Any]) -> dict[str, Any]:
        title = self._pick_string(item, "Name", "name", "title", "ProductName", "productname") or "Untitled Impact product"
        product_url = self._pick_string(item, "ProductUrl", "producturl", "product_url", "url")
        affiliate_url = self._pick_string(item, "TrackingUrl", "trackingurl", "tracking_url", "deeplink", "deep_link") or product_url or "https://impact.com/"
        current = self._pick_number(item, "CurrentPrice", "currentprice", "current_price", "Price", "price") or 1
        old = self._pick_number(item, "OriginalPrice", "originalprice", "old_price", "WasPrice", "wasprice") or current

        return {
            "id": self._pick_string(item, "Id", "id", "Sku", "sku", "ProductId", "productid") or self._stable_id(item, prefix="impact"),
            "title": title,
            "description": self._pick_string(item, "Description", "description", "short_description") or title,
            "imageUrl": self._pick_string(item, "ImageUrl", "imageurl", "image_url", "image") or "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=1200",
            "platform": self._pick_string(item, "AdvertiserName", "advertisername", "advertiser_name", "Brand", "brand") or "Impact Merchant",
            "category": self._pick_string(item, "Category", "category", "category_name") or "Other",
            "oldPrice": old,
            "currentPrice": current,
            "currency": self._pick_currency(item) or "USD",
            "productUrl": product_url or affiliate_url,
            "affiliateUrl": affiliate_url,
            "rating": self._pick_number(item, "Rating", "rating", "average_rating") or 0,
            "reviewCount": int(self._pick_number(item, "ReviewCount", "review_count", "reviews") or 0),
            "freeShipping": self._pick_bool(item, "FreeShipping", "free_shipping", "free_delivery", "shipping_free"),
            "verified": True,
            "shipsTo": self._pick_list(item, "ShipsTo", "ships_to", "countries", "shipping_countries"),
            "hotDeal": True if old > current and ((old - current) / old) >= 0.3 else False,
            "lowestPrice": self._pick_bool(item, "LowestPrice", "lowest_price", "best_price"),
        }

    def _normalize_mercadolibre(self, item: dict[str, Any]) -> dict[str, Any]:
        title = self._pick_string(item, "title") or "Untitled Mercado Libre item"
        product_url = self._pick_string(item, "permalink") or "https://www.mercadolibre.com/"
        current = self._pick_number(item, "price") or 1
        original = self._pick_number(item, "original_price")
        base = self._pick_number(item, "base_price")
        old = original if original and original > current else base if base and base > current else current
        currency = self._pick_string(item, "currency_id") or "USD"

        image_url = (
            self._pick_string(item, "secure_thumbnail", "thumbnail")
            or "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=1200"
        )
        if image_url.startswith("http://"):
            image_url = "https://" + image_url.removeprefix("http://")

        site_id = self._pick_string(item, "_discount_hub_site_id", "site_id") or "ML"
        site_name = self._pick_string(item, "_discount_hub_site_name") or f"Mercado Libre {site_id}"
        site_country = self._pick_string(item, "_discount_hub_site_country") or site_id[-2:].upper()
        query = self._pick_string(item, "_discount_hub_query") or ""

        shipping = item.get("shipping")
        free_shipping = False
        if isinstance(shipping, dict):
            free_shipping = bool(shipping.get("free_shipping"))

        discount = ((old - current) / old) if old > 0 else 0
        item_id = self._pick_string(item, "id") or self._stable_id(item, prefix="mercadolibre")

        return {
            "id": f"mercadolibre_{site_id.lower()}_{item_id}",
            "title": title,
            "description": self._build_mercadolibre_description(item, title),
            "imageUrl": image_url,
            "platform": site_name,
            "category": self._mercadolibre_category(query=query, title=title),
            "oldPrice": round(old, 2),
            "currentPrice": round(current, 2),
            "currency": currency.upper()[:3],
            "productUrl": product_url,
            "affiliateUrl": product_url,
            "rating": 0,
            "reviewCount": 0,
            "freeShipping": free_shipping,
            "verified": True,
            "shipsTo": [site_country.upper()],
            "hotDeal": discount >= 0.2,
            "lowestPrice": False,
        }

    def _build_mercadolibre_description(self, item: dict[str, Any], title: str) -> str:
        condition = self._pick_string(item, "condition")
        listing_type = self._pick_string(item, "listing_type_id")
        parts = [title]
        if condition:
            parts.append(f"Condition: {condition}")
        if listing_type:
            parts.append(f"Listing: {listing_type}")
        return " · ".join(parts)

    def _mercadolibre_category(self, *, query: str, title: str) -> str:
        text = f" {query} {title} ".lower()
        if any(value in text for value in ("laptop", "notebook", "portatil", "portátil", "computadora", "computador", "macbook")):
            return "Computers"
        if any(value in text for value in ("audifono", "audífono", "auricular", "fone", "headphone", "smartwatch", "smart watch", "reloj inteligente", "celular", "smartphone")):
            return "Electronics"
        if any(value in text for value in ("tenis", "tênis", "zapatilla", "zapatillas", "sneaker", "sneakers", "calzado", "sapato")):
            return "Fashion"
        if any(value in text for value in ("gaming", "gamer", "juego", "controle", "control", "teclado", "mouse")):
            return "Gaming"
        if any(value in text for value in ("casa", "hogar", "home", "smart home", "cocina")):
            return "Home"
        return "Other"

    def _normalize_ebay_browse(self, item: dict[str, Any]) -> dict[str, Any]:
        title = self._pick_string(item, "title") or "Untitled eBay item"
        item_id = self._pick_string(item, "itemId", "legacyItemId") or self._stable_id(item, prefix="ebay")
        marketplace_id = self._pick_string(item, "listingMarketplaceId") or "eBay"
        raw_product_url = self._pick_string(item, "itemWebUrl") or "https://www.ebay.com/"
        product_url = self._canonical_ebay_item_url(raw_product_url, item_id=item_id, marketplace_id=marketplace_id) or raw_product_url
        raw_affiliate_url = self._pick_string(item, "itemAffiliateWebUrl")
        affiliate_url = raw_affiliate_url or product_url
        price = self._nested_number(item, "price", "value") or 1
        currency = self._nested_string(item, "price", "currency") or "USD"

        original_price = self._nested_number(item, "marketingPrice", "originalPrice", "value")
        if original_price is None:
            original_price = self._nested_number(item, "marketingPrice", "originalPrice", "convertedFromValue")
        old = original_price if original_price and original_price > price else price
        current = price

        discount_percentage = self._nested_number(item, "marketingPrice", "discountPercentage")
        if discount_percentage and old <= current:
            old = current / max(1 - (discount_percentage / 100), 0.01)

        shipping_options = item.get("shippingOptions")
        free_shipping = False
        ships_to: list[str] = []
        if isinstance(shipping_options, list):
            for option in shipping_options:
                if not isinstance(option, dict):
                    continue
                shipping_cost = self._nested_number(option, "shippingCost", "value")
                if shipping_cost == 0:
                    free_shipping = True
                ship_to_locations = option.get("shipToLocations")
                if isinstance(ship_to_locations, list):
                    ships_to.extend(str(value).upper() for value in ship_to_locations if str(value).strip())

        categories = item.get("categories")
        category = "eBay"
        if isinstance(categories, list) and categories:
            first = categories[0]
            if isinstance(first, dict):
                category = self._pick_string(first, "categoryName", "categoryId") or category

        image = item.get("image")
        image_url = "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=1200"
        if isinstance(image, dict):
            image_url = self._pick_string(image, "imageUrl") or image_url

        discount = ((old - current) / old) if old > 0 else 0
        marketplace_key = re.sub(r"[^A-Z0-9]+", "_", marketplace_id.upper()).strip("_").lower() or "global"

        return {
            "id": f"ebay_{marketplace_key}_{item_id}",
            "title": title,
            "description": self._pick_string(item, "shortDescription", "subtitle") or title,
            "imageUrl": image_url,
            "platform": marketplace_id.replace("EBAY_", "eBay ") if marketplace_id.startswith("EBAY_") else "eBay",
            "category": category,
            "oldPrice": round(old, 2),
            "currentPrice": round(current, 2),
            "currency": currency.upper()[:3],
            "productUrl": product_url,
            "affiliateUrl": affiliate_url,
            "rating": 0,
            "reviewCount": 0,
            "freeShipping": free_shipping,
            "verified": True,
            "shipsTo": sorted(set(ships_to)),
            "hotDeal": discount >= 0.3,
            "lowestPrice": False,
        }

    def _repair_admitad_aliexpress_url(self, url: str | None, product_url: str | None) -> str | None:
        return admitad_deeplink_service.build_manual_deeplink(url, product_url)

    def _build_admitad_deeplink(self, base_url: str | None, product_url: str | None) -> str | None:
        return admitad_deeplink_service.build_manual_deeplink(base_url, product_url)

    def _is_admitad_tracking_url(self, url: str | None) -> bool:
        return admitad_deeplink_service.is_admitad_tracking_url(url)

    def _extract_aliexpress_product_url(self, value: str | None) -> str | None:
        target = admitad_deeplink_service.extract_target_url(value)
        if not target:
            return None
        parsed = urllib.parse.urlparse(target)
        if "aliexpress." in parsed.netloc.lower() and "/item/" in parsed.path:
            return urllib.parse.urlunparse(parsed._replace(query="", fragment=""))
        return None

    def _canonical_ebay_item_url(self, url: str | None, *, item_id: str, marketplace_id: str) -> str | None:
        legacy_id = self._ebay_legacy_item_id(item_id)
        if not legacy_id:
            return None

        host = self._ebay_marketplace_host(marketplace_id)
        if url:
            parsed = urllib.parse.urlparse(url)
            if "ebay." in parsed.netloc.lower():
                host = parsed.netloc
        return f"https://{host}/itm/{legacy_id}"

    def _ebay_legacy_item_id(self, item_id: str | None) -> str | None:
        if not item_id:
            return None
        text = str(item_id)
        match = re.search(r"\|(\d{6,})\|", text)
        if match:
            return match.group(1)
        match = re.search(r"(\d{6,})", text)
        if match:
            return match.group(1)
        return None

    def _ebay_marketplace_host(self, marketplace_id: str) -> str:
        mapping = {
            "EBAY_US": "www.ebay.com",
            "EBAY_GB": "www.ebay.co.uk",
            "EBAY_DE": "www.ebay.de",
            "EBAY_FR": "www.ebay.fr",
            "EBAY_IT": "www.ebay.it",
            "EBAY_ES": "www.ebay.es",
            "EBAY_AU": "www.ebay.com.au",
            "EBAY_CA": "www.ebay.ca",
            "EBAY_MOTORS_US": "www.ebay.com",
        }
        return mapping.get(str(marketplace_id or "").upper(), "www.ebay.com")

    def _nested_value(self, item: dict[str, Any], *path: str) -> Any:
        current: Any = item
        for key in path:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
        return current

    def _nested_string(self, item: dict[str, Any], *path: str) -> str | None:
        value = self._nested_value(item, *path)
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _nested_number(self, item: dict[str, Any], *path: str) -> float | None:
        value = self._nested_value(item, *path)
        if value is None or value == "":
            return None
        if isinstance(value, int | float):
            return float(value)
        return self._pick_number({"value": value}, "value")

    def _pick_string(self, item: dict[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = item.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return None

    def _pick_number(self, item: dict[str, Any], *keys: str) -> float | None:
        for key in keys:
            value = item.get(key)
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

    def _infer_awin_currency(self, item: dict[str, Any]) -> str:
        # Prefer explicit feed values in _pick_currency(). This fallback is only
        # used when an Awin native feed sends bare numeric prices.
        advertiser_id = self._pick_string(
            item,
            "_awin_advertiser_id",
            "advertiser_id",
            "merchant_id",
            "programme_id",
            "program_id",
        ) or ""
        feed_name = self._pick_string(item, "_awin_feed_name", "feed_name") or ""
        region = self._pick_string(item, "_awin_feed_region", "programme_region", "region", "country", "market") or ""
        merchant_url = self._pick_string(
            item,
            "merchant_product_url",
            "merchant_deep_link",
            "product_url",
            "url",
            "link",
        ) or ""

        hint = re.sub(r"[^a-z0-9]+", " ", f"{feed_name} {region}".lower()).strip()
        hint_tokens = set(hint.split())
        if "eu" in hint_tokens or "europe" in hint_tokens or "european" in hint_tokens:
            return "EUR"
        if "uk" in hint_tokens or "gb" in hint_tokens or "britain" in hint_tokens:
            return "GBP"
        if "pl" in hint_tokens or "poland" in hint_tokens:
            return "PLN"
        if "au" in hint_tokens or "australia" in hint_tokens:
            return "AUD"
        if "ca" in hint_tokens or "canada" in hint_tokens:
            return "CAD"
        if "dk" in hint_tokens or "denmark" in hint_tokens:
            return "DKK"
        if "se" in hint_tokens or "sweden" in hint_tokens:
            return "SEK"
        if "no" in hint_tokens or "norway" in hint_tokens:
            return "NOK"

        host = urllib.parse.urlparse(merchant_url).netloc.lower().split(":", 1)[0]
        if host.endswith(".co.uk") or host.endswith(".uk"):
            return "GBP"
        if host.endswith(".com.au") or host.endswith(".au"):
            return "AUD"
        if host.endswith(".ca"):
            return "CAD"
        if host.endswith(".pl"):
            return "PLN"
        if host.endswith(".dk"):
            return "DKK"
        if host.endswith(".se"):
            return "SEK"
        if host.endswith(".no"):
            return "NOK"
        if host.endswith((".de", ".fr", ".es", ".it", ".nl", ".be", ".at", ".ie", ".pt", ".fi")):
            return "EUR"

        # TTfone's main Shopify/Awin feeds are UK/GBP; the dedicated EU feed
        # is handled above from its "Shopify EU" feed name.
        if advertiser_id.strip() == "28737":
            return "GBP"
        return "USD"

    def _pick_currency(self, item: dict[str, Any]) -> str | None:
        direct = self._pick_string(item, "currency", "currency_code", "currencyCode")
        if direct:
            return direct.upper()[:3]

        for key in (
            "price",
            "sale_price",
            "special_price",
            "promo_price",
            "promotional_price",
            "offer_price",
            "current_price",
            "old_price",
            "recommended_retail_price",
            "merchant_product_price",
            "merchant_product_price_old",
            "oldPrice",
            "currentPrice",
            "product_price",
            "product_price_old",
        ):
            value = item.get(key)
            if value is None:
                continue
            text = str(value).upper()
            match = re.search(r"\b(USD|EUR|GBP|UZS|TRY|AED|AUD|CAD|JPY|CNY|CHF|SEK|NOK|DKK|PLN)\b", text)
            if match:
                return match.group(1)
            if "$" in text:
                return "USD"
            if "€" in text:
                return "EUR"
            if "£" in text:
                return "GBP"
        return None

    def _pick_bool(self, item: dict[str, Any], *keys: str, default: bool = False) -> bool:
        for key in keys:
            value = item.get(key)
            if isinstance(value, bool):
                return value
            if isinstance(value, int | float):
                return value != 0
            if isinstance(value, str):
                text = value.strip().lower()
                if text in {"true", "1", "yes", "y", "free", "available"}:
                    return True
                if text in {"false", "0", "no", "n", "paid", "unavailable"}:
                    return False
        return default

    def _pick_list(self, item: dict[str, Any], *keys: str) -> list[str]:
        for key in keys:
            value = item.get(key)
            if value is None:
                continue
            if isinstance(value, list):
                return [str(item).upper().strip() for item in value if str(item).strip()]
            if isinstance(value, str):
                return [part.upper().strip() for part in re.split(r"[,;|]", value) if part.strip()]
        return []

    def _replace_known_mojibake(self, text: str) -> str:
        euro = chr(0x20AC)
        pound = chr(0x00A3)
        bullet = chr(0x2022)
        apostrophe = "'"
        dash = chr(0x2013)
        long_dash = chr(0x2014)

        c2 = chr(0x00C2)
        e2 = chr(0x00E2)
        ac = chr(0x00AC)
        lsq = chr(0x2018)
        rsq = chr(0x2019)
        ldq = chr(0x201C)
        rdq = chr(0x201D)

        replacements = {
            e2 + chr(0x0082) + ac: euro,
            e2 + chr(0x201A) + ac: euro,
            e2 + ac: euro,
            c2 + chr(0x00A3): pound,
            c2 + "$": "$",
            c2 + " ": " ",
            c2 + chr(0x00A0): " ",
            e2 + chr(0x0080) + chr(0x0099): apostrophe,
            e2 + chr(0x20AC) + chr(0x2122): apostrophe,
            e2 + rsq: apostrophe,
            e2 + chr(0x0080) + chr(0x0098): apostrophe,
            e2 + chr(0x20AC) + chr(0x02DC): apostrophe,
            e2 + lsq: apostrophe,
            e2 + chr(0x0080) + chr(0x009C): '"',
            e2 + chr(0x20AC) + chr(0x0153): '"',
            e2 + ldq: '"',
            e2 + chr(0x0080) + chr(0x009D): '"',
            e2 + chr(0x20AC) + chr(0x009D): '"',
            e2 + rdq: '"',
            e2 + chr(0x0080) + chr(0x0093): dash,
            e2 + chr(0x20AC) + chr(0x201C): dash,
            e2 + chr(0x0080) + chr(0x0094): long_dash,
            e2 + chr(0x20AC) + chr(0x201D): long_dash,
            e2 + chr(0x0080) + chr(0x00A2): bullet,
            e2 + chr(0x20AC) + chr(0x00A2): bullet,
            e2 + chr(0x00A2): bullet,
            chr(0x00EF) + chr(0x00BB) + chr(0x00BF): "",
            chr(0xFEFF): "",
        }
        for bad, good in replacements.items():
            text = text.replace(bad, good)

        text = text.replace(e2 + ac, euro)
        text = text.replace(c2 + chr(0x00A3), pound)
        text = re.sub(e2 + r"(?=s\b)", apostrophe, text)
        text = re.sub(r"(?m)^\s*" + e2 + r"\s+", bullet + " ", text)
        return text

    def _clean_text(self, value: str | None) -> str:
        if value is None:
            return ""
        text = html.unescape(str(value)).strip()
        if not text:
            return ""

        text = self._replace_known_mojibake(text)
        for _ in range(2):
            before_score = len(re.findall(r"[\u00c2\u00c3\u00e2\ufffd]", text))
            best = text
            for encoding in ("latin1", "cp1252"):
                try:
                    candidate = text.encode(encoding).decode("utf-8")
                except UnicodeError:
                    continue
                candidate = self._replace_known_mojibake(candidate)
                candidate_score = len(re.findall(r"[\u00c2\u00c3\u00e2\ufffd]", candidate))
                if candidate_score < before_score:
                    best = candidate
                    before_score = candidate_score
            if best == text:
                break
            text = best

        text = self._replace_known_mojibake(text)
        replacements = {
            "â‚¬": "€",
            "â¬": "€",
            "Â£": "£",
            "Â$": "$",
            "ï¼š": ":",
            "ï¼": ":",
            "：": ":",
            " ": " ",
        }
        for bad, good in replacements.items():
            text = text.replace(bad, good)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _safe_key(self, value: str) -> str:
        key = re.sub(r"[^a-zA-Z0-9]+", "_", str(value or "").strip().lower()).strip("_")
        return key[:96]

    def _stable_id(self, item: dict[str, Any], *, prefix: str) -> str:
        source = "|".join(
            str(item.get(key, ""))
            for key in ("id", "sku", "product_id", "productId", "productid", "url", "link", "productUrl", "producturl", "title", "name", "product_name", "productname")
        )
        digest = hashlib.sha1(source.encode("utf-8")).hexdigest()[:12]
        return f"{prefix}_{digest}"


feed_adapter_service = FeedAdapterService()
