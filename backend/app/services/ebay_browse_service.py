from __future__ import annotations

import base64
import json
import time
from datetime import datetime, timezone
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status

from app.core.config import get_settings


DEFAULT_BAD_EBAY_KEYWORDS = {
    "as is",
    "box only",
    "broken",
    "cable only",
    "case only",
    "charger only",
    "cover only",
    "damaged",
    "defect",
    "defective",
    "display only",
    "empty box",
    "faulty",
    "for parts",
    "for repair",
    "housing only",
    "lcd screen only",
    "logic board",
    "mainboard",
    "manual only",
    "motherboard",
    "non working",
    "not working",
    "parts only",
    "read description",
    "read listing",
    "repair only",
    "replacement",
    "screen protector",
    "shell only",
    "spare parts",
    "spares",
    "tempered glass",
    "untested",
    "unknown condition",
    # Non-product / low-quality eBay listings that often look like discounts
    # but are not useful product offers for DiscountHub users.
    "auction only",
    "bid only",
    "digital download",
    "download only",
    "instructions",
    "instruction only",
    "lot only",
    "photo only",
    "picture only",
    "poster only",
    "software key",
    "sticker only",
    "unlock service",
    "virtual item",
    "warranty only",
}

DEFAULT_BAD_EBAY_CONDITION_TERMS = {
    "for parts",
    "not working",
    "parts only",
    "seller refurbished",
    "spares",
    "non working",
    "defective",
    "damaged",
}


@dataclass
class _CachedToken:
    access_token: str
    expires_at_epoch: float


class EbayBrowseService:
    """Fetches eBay Browse API search results using app OAuth credentials."""

    def __init__(self) -> None:
        self._cached_token: _CachedToken | None = None

    def search_from_provider_url(self, provider_url: str, *, timeout_seconds: int) -> list[dict[str, Any]]:
        settings = get_settings()
        if not settings.ebay_client_id.strip() or not settings.ebay_client_secret.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "eBay Browse API credentials are not configured. "
                    "Set EBAY_CLIENT_ID and EBAY_CLIENT_SECRET before enabling eBay providers."
                ),
            )

        query = self._parse_provider_url(provider_url)
        token = self._get_access_token(timeout_seconds=timeout_seconds)
        search_url = self._build_search_url(query)

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "DiscountHub-eBay-Browse-Adapter/0.1",
            "X-EBAY-C-MARKETPLACE-ID": query["marketplace_id"],
        }

        # Needed to make returned URLs affiliate-ready when the account/campaign is configured.
        end_user_context = self._build_end_user_context(
            campaign_id=settings.ebay_campaign_id,
            reference_id=settings.ebay_reference_id,
        )
        if end_user_context:
            headers["X-EBAY-C-ENDUSERCTX"] = end_user_context

        raw_data = self._fetch_json(search_url, headers=headers, timeout_seconds=timeout_seconds)
        item_summaries = raw_data.get("itemSummaries", []) if isinstance(raw_data, dict) else []
        if not isinstance(item_summaries, list):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="eBay Browse API response did not contain an itemSummaries array.",
            )

        result: list[dict[str, Any]] = []
        seen_item_keys: set[str] = set()
        for item in item_summaries:
            if not isinstance(item, dict):
                continue
            item_key = self._item_dedupe_key(item)
            if item_key in seen_item_keys:
                continue
            seen_item_keys.add(item_key)
            result.append(item)
        return self._apply_local_quality_filters(result, query)

    def _parse_provider_url(self, provider_url: str) -> dict[str, str]:
        settings = get_settings()
        value = provider_url.strip()
        if not value.startswith("ebay://browse"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="eBay Browse providers must use ebay://browse?... URL format.",
            )

        parsed = urllib.parse.urlparse(value)
        params = urllib.parse.parse_qs(parsed.query)

        q = self._single(params, "q") or "deals"
        marketplace_id = self._single(params, "marketplace_id") or settings.ebay_default_marketplace_id
        limit = self._single(params, "limit") or "50"
        offset = self._single(params, "offset") or "0"
        category_ids = self._single(params, "category_ids")
        filter_value = self._single(params, "filter")
        sort = self._single(params, "sort")

        # Local quality filters are DiscountHub-only query params. They are not
        # sent to eBay, but let each provider config avoid obvious bad listings
        # such as broken/parts-only items while still using the official Browse API.
        min_price = self._single(params, "min_price") or ""
        min_discount = self._single(params, "min_discount") or ""
        exclude_keywords = self._single(params, "exclude_keywords") or ""

        # DiscountHub-only quality controls. Defaults are intentionally strict
        # because eBay search results can include auctions, parts-only listings,
        # screen protectors, manuals and old unavailable pages that look like
        # product deals but create bad UX in the app.
        max_price = self._single(params, "max_price") or ""
        max_discount = self._single(params, "max_discount") or "85"
        require_fixed_price = self._single(params, "require_fixed_price") or "true"
        require_image = self._single(params, "require_image") or "true"
        require_clickable_url = self._single(params, "require_clickable_url") or "true"
        min_seller_feedback_percent = self._single(params, "min_seller_feedback_percent") or "90"
        min_seller_feedback_score = self._single(params, "min_seller_feedback_score") or "5"
        reject_conditions = self._single(params, "reject_conditions") or ""

        return {
            "q": q[:100],
            "marketplace_id": marketplace_id,
            "limit": limit,
            "offset": offset,
            "category_ids": category_ids or "",
            "filter": filter_value or "",
            "sort": sort or "",
            "min_price": min_price,
            "max_price": max_price,
            "min_discount": min_discount,
            "max_discount": max_discount,
            "exclude_keywords": exclude_keywords,
            "require_fixed_price": require_fixed_price,
            "require_image": require_image,
            "require_clickable_url": require_clickable_url,
            "min_seller_feedback_percent": min_seller_feedback_percent,
            "min_seller_feedback_score": min_seller_feedback_score,
            "reject_conditions": reject_conditions,
        }

    def _build_search_url(self, query: dict[str, str]) -> str:
        settings = get_settings()
        base = settings.ebay_api_base_url.rstrip("/")
        params: dict[str, str] = {
            "q": query["q"],
            "limit": query["limit"],
            "offset": query["offset"],
            "fieldgroups": "EXTENDED",
        }
        if query["category_ids"]:
            params["category_ids"] = query["category_ids"]
        if query["filter"]:
            params["filter"] = query["filter"]
        if query["sort"]:
            params["sort"] = query["sort"]

        return f"{base}/buy/browse/v1/item_summary/search?{urllib.parse.urlencode(params)}"


    def _apply_local_quality_filters(
        self,
        items: list[dict[str, Any]],
        query: dict[str, str],
    ) -> list[dict[str, Any]]:
        min_price = self._parse_float(query.get("min_price", ""))
        max_price = self._parse_float(query.get("max_price", ""))
        min_discount = self._parse_float(query.get("min_discount", ""))
        max_discount = self._parse_float(query.get("max_discount", ""))
        require_fixed_price = self._parse_bool(query.get("require_fixed_price", "true"), default=True)
        require_image = self._parse_bool(query.get("require_image", "true"), default=True)
        require_clickable_url = self._parse_bool(query.get("require_clickable_url", "true"), default=True)
        min_seller_feedback_percent = self._parse_float(query.get("min_seller_feedback_percent", "90"))
        min_seller_feedback_score = self._parse_float(query.get("min_seller_feedback_score", "5"))
        reject_condition_terms = sorted(
            {
                *(keyword.strip().lower() for keyword in query.get("reject_conditions", "").split("|") if keyword.strip()),
                *DEFAULT_BAD_EBAY_CONDITION_TERMS,
            }
        )
        exclude_keywords = sorted(
            {
                *(keyword.strip().lower() for keyword in query.get("exclude_keywords", "").split("|") if keyword.strip()),
                *DEFAULT_BAD_EBAY_KEYWORDS,
            }
        )

        filtered: list[dict[str, Any]] = []
        for item in items:
            title = str(item.get("title") or "").lower()
            description = str(item.get("shortDescription") or item.get("subtitle") or "").lower()
            condition = str(item.get("condition") or "").lower()
            searchable_text = f"{title} {description} {condition}"

            if exclude_keywords and any(keyword in searchable_text for keyword in exclude_keywords):
                continue
            if reject_condition_terms and any(term in condition for term in reject_condition_terms):
                continue

            if require_fixed_price and not self._has_fixed_price_buying_option(item):
                continue

            if require_image and not self._has_real_image(item):
                continue

            if require_clickable_url and not self._has_clickable_item_url(item):
                continue

            if self._is_ended_listing(item):
                continue

            if self._is_unavailable_item(item):
                continue

            price = self._nested_number(item, "price", "value")
            if min_price is not None and price is not None and price < min_price:
                continue
            if max_price is not None and price is not None and price > max_price:
                continue

            discount = self._discount_percent(item)
            if min_discount is not None:
                if discount is None or discount < min_discount:
                    continue
            if max_discount is not None and discount is not None and discount > max_discount:
                # Very high eBay "discounts" are often inflated list prices or
                # low-quality listings. Keep this bounded for user trust.
                continue

            if not self._seller_meets_quality_bar(
                item,
                min_feedback_percent=min_seller_feedback_percent,
                min_feedback_score=min_seller_feedback_score,
            ):
                continue

            filtered.append(item)
        return filtered

    def _has_fixed_price_buying_option(self, item: dict[str, Any]) -> bool:
        options = item.get("buyingOptions")
        if not isinstance(options, list):
            # Older/partial API responses may omit the field. Do not reject only
            # because it is missing, but reject explicit auction-only listings.
            return True
        normalized = {str(value).upper().strip() for value in options if str(value).strip()}
        if "FIXED_PRICE" in normalized or "BUY_IT_NOW" in normalized:
            return True
        if "AUCTION" in normalized and len(normalized) == 1:
            return False
        return True

    def _has_real_image(self, item: dict[str, Any]) -> bool:
        image = item.get("image")
        image_url = ""
        if isinstance(image, dict):
            image_url = str(image.get("imageUrl") or "").strip().lower()
        if not image_url.startswith(("http://", "https://")):
            return False
        blocked = ("placeholder", "no_image", "noimage", "gif;base64")
        return not any(value in image_url for value in blocked)

    def _has_clickable_item_url(self, item: dict[str, Any]) -> bool:
        url = str(item.get("itemAffiliateWebUrl") or item.get("itemWebUrl") or "").strip().lower()
        if not url.startswith(("http://", "https://")):
            return False
        return "/itm/" in url or "ebay." in url

    def _is_ended_listing(self, item: dict[str, Any]) -> bool:
        end_date = str(item.get("itemEndDate") or "").strip()
        if not end_date:
            return False
        try:
            parsed = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        except ValueError:
            return False
        return parsed < datetime.now(timezone.utc)

    def _is_unavailable_item(self, item: dict[str, Any]) -> bool:
        """Reject eBay rows that explicitly say the item is not purchasable.

        Browse API search summaries do not always include stock data, so missing
        availability is treated as unknown and allowed. But when eBay gives
        `OUT_OF_STOCK`, `UNAVAILABLE`, or an explicit zero quantity, the item is
        bad UX for DiscountHub and should not be imported.
        """
        availability_rows: list[Any] = []
        estimated = item.get("estimatedAvailabilities")
        if isinstance(estimated, list):
            availability_rows.extend(estimated)

        for key in (
            "availability",
            "availabilityStatus",
            "estimatedAvailabilityStatus",
            "itemAvailabilityStatus",
        ):
            value = item.get(key)
            if value not in (None, ""):
                availability_rows.append(value)

        if not availability_rows:
            return False

        bad_status_markers = (
            "OUT_OF_STOCK",
            "OUT OF STOCK",
            "SOLD_OUT",
            "SOLD OUT",
            "UNAVAILABLE",
            "NOT_AVAILABLE",
            "NOT AVAILABLE",
            "ENDED",
        )
        quantity_keys = (
            "estimatedAvailableQuantity",
            "availableQuantity",
            "quantityAvailable",
            "quantity",
        )

        for row in availability_rows:
            if isinstance(row, dict):
                status_text = " ".join(
                    str(row.get(key) or "").strip().upper()
                    for key in ("estimatedAvailabilityStatus", "availabilityStatus", "status")
                )
                if status_text and any(marker in status_text for marker in bad_status_markers):
                    return True
                for key in quantity_keys:
                    quantity = self._number_from_value(row.get(key))
                    if quantity is not None and quantity <= 0:
                        return True
                continue

            status_text = str(row or "").strip().upper()
            if status_text and any(marker in status_text for marker in bad_status_markers):
                return True

        return False

    def _seller_meets_quality_bar(
        self,
        item: dict[str, Any],
        *,
        min_feedback_percent: float | None,
        min_feedback_score: float | None,
    ) -> bool:
        seller = item.get("seller")
        if not isinstance(seller, dict):
            return True
        feedback_percent = self._nested_number(item, "seller", "feedbackPercentage")
        feedback_score = self._nested_number(item, "seller", "feedbackScore")
        if min_feedback_percent is not None and feedback_percent is not None and feedback_percent < min_feedback_percent:
            return False
        if min_feedback_score is not None and feedback_score is not None and feedback_score < min_feedback_score:
            return False
        return True

    def _item_dedupe_key(self, item: dict[str, Any]) -> str:
        item_id = str(item.get("itemId") or item.get("legacyItemId") or "").strip().lower()
        if item_id:
            return item_id

        title = str(item.get("title") or "").strip().lower()
        price = str(self._nested_number(item, "price", "value") or "").strip()
        seller = ""
        seller_info = item.get("seller")
        if isinstance(seller_info, dict):
            seller = str(seller_info.get("username") or seller_info.get("sellerUsername") or "").strip().lower()
        return f"{seller}|{title}|{price}"

    def _discount_percent(self, item: dict[str, Any]) -> float | None:
        """Returns the item discount percent when eBay exposes enough price data.

        eBay can return the discount directly as marketingPrice.discountPercentage,
        or it can return current price + originalPrice. DiscountHub is a discount
        aggregator, so local filters should reject regular catalog listings where
        eBay only gives a single current price.
        """
        direct_discount = self._nested_number(item, "marketingPrice", "discountPercentage")
        if direct_discount is not None:
            return direct_discount

        current_price = self._nested_number(item, "price", "value")
        original_price = self._nested_number(item, "marketingPrice", "originalPrice", "value")
        if original_price is None:
            original_price = self._nested_number(item, "marketingPrice", "originalPrice", "convertedFromValue")

        if current_price is None or original_price is None or original_price <= current_price or original_price <= 0:
            return None

        return ((original_price - current_price) / original_price) * 100

    def _parse_float(self, value: str) -> float | None:
        text = str(value or "").strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None

    def _parse_bool(self, value: str | None, *, default: bool = False) -> bool:
        text = str(value or "").strip().lower()
        if text in {"1", "true", "yes", "y", "on"}:
            return True
        if text in {"0", "false", "no", "n", "off"}:
            return False
        return default

    def _nested_value(self, item: dict[str, Any], *path: str) -> Any:
        current: Any = item
        for key in path:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
        return current

    def _nested_number(self, item: dict[str, Any], *path: str) -> float | None:
        return self._number_from_value(self._nested_value(item, *path))

    def _number_from_value(self, value: Any) -> float | None:
        if value is None or value == "":
            return None
        if isinstance(value, int | float):
            return float(value)
        try:
            return float(str(value).replace(",", "").strip())
        except ValueError:
            return None

    def _get_access_token(self, *, timeout_seconds: int) -> str:
        now = time.time()
        if self._cached_token and self._cached_token.expires_at_epoch > now + 60:
            return self._cached_token.access_token

        settings = get_settings()
        credentials = f"{settings.ebay_client_id}:{settings.ebay_client_secret}".encode("utf-8")
        encoded_credentials = base64.b64encode(credentials).decode("ascii")
        body = urllib.parse.urlencode(
            {
                "grant_type": "client_credentials",
                "scope": settings.ebay_scope,
            }
        ).encode("utf-8")

        response = self._fetch_json(
            settings.ebay_oauth_url,
            headers={
                "Authorization": f"Basic {encoded_credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "User-Agent": "DiscountHub-eBay-Browse-Adapter/0.1",
            },
            body=body,
            timeout_seconds=timeout_seconds,
        )

        access_token = str(response.get("access_token", "")).strip() if isinstance(response, dict) else ""
        expires_in = int(response.get("expires_in", 7200)) if isinstance(response, dict) else 7200
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="eBay OAuth response did not include access_token.",
            )

        self._cached_token = _CachedToken(
            access_token=access_token,
            expires_at_epoch=time.time() + max(expires_in, 60),
        )
        return access_token

    def _fetch_json(
        self,
        url: str,
        *,
        headers: dict[str, str],
        timeout_seconds: int,
        body: bytes | None = None,
    ) -> Any:
        try:
            request = urllib.request.Request(url, data=body, headers=headers)
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                raw_body = response.read().decode(charset)
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"eBay API returned HTTP {exc.code}: {error_body[:500]}",
            ) from exc
        except urllib.error.URLError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not reach eBay API: {exc}",
            ) from exc

        try:
            return json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"eBay API did not return valid JSON: {exc}",
            ) from exc

    def _build_end_user_context(self, *, campaign_id: str, reference_id: str) -> str:
        parts: list[str] = []
        if campaign_id.strip():
            parts.append(f"affiliateCampaignId={campaign_id.strip()}")
        if reference_id.strip():
            parts.append(f"affiliateReferenceId={reference_id.strip()}")
        return ",".join(parts)

    def _single(self, params: dict[str, list[str]], key: str) -> str | None:
        values = params.get(key)
        if not values:
            return None
        value = values[0].strip()
        return value or None


ebay_browse_service = EbayBrowseService()
