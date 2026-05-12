from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status

from app.core.config import get_settings


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
        for item in item_summaries:
            if isinstance(item, dict):
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

        return {
            "q": q[:100],
            "marketplace_id": marketplace_id,
            "limit": limit,
            "offset": offset,
            "category_ids": category_ids or "",
            "filter": filter_value or "",
            "sort": sort or "",
            "min_price": min_price,
            "min_discount": min_discount,
            "exclude_keywords": exclude_keywords,
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
        min_discount = self._parse_float(query.get("min_discount", ""))
        exclude_keywords = [
            keyword.strip().lower()
            for keyword in query.get("exclude_keywords", "").split("|")
            if keyword.strip()
        ]

        filtered: list[dict[str, Any]] = []
        for item in items:
            title = str(item.get("title") or "").lower()
            description = str(item.get("shortDescription") or item.get("subtitle") or "").lower()
            searchable_text = f"{title} {description}"

            if exclude_keywords and any(keyword in searchable_text for keyword in exclude_keywords):
                continue

            price = self._nested_number(item, "price", "value")
            if min_price is not None and price is not None and price < min_price:
                continue

            if min_discount is not None:
                discount = self._discount_percent(item)
                if discount is None or discount < min_discount:
                    continue

            filtered.append(item)
        return filtered

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

    def _nested_value(self, item: dict[str, Any], *path: str) -> Any:
        current: Any = item
        for key in path:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
        return current

    def _nested_number(self, item: dict[str, Any], *path: str) -> float | None:
        value = self._nested_value(item, *path)
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
