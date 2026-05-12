from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from fastapi import HTTPException, status


_SITE_NAMES: dict[str, str] = {
    "MLA": "Mercado Libre Argentina",
    "MLB": "Mercado Livre Brazil",
    "MLM": "Mercado Libre Mexico",
    "MLC": "Mercado Libre Chile",
    "MCO": "Mercado Libre Colombia",
    "MPE": "Mercado Libre Peru",
    "MLU": "Mercado Libre Uruguay",
}

_SITE_COUNTRIES: dict[str, str] = {
    "MLA": "AR",
    "MLB": "BR",
    "MLM": "MX",
    "MLC": "CL",
    "MCO": "CO",
    "MPE": "PE",
    "MLU": "UY",
}


class MercadoLibreService:
    """Fetches Mercado Libre public marketplace search results.

    This adapter is intentionally data-first: it does not require an affiliate
    account, app approval, or private user access. Provider URLs use the local
    format mercadolibre://search?... and are translated into the official
    /sites/{site_id}/search API endpoint.
    """

    def search_from_provider_url(self, provider_url: str, *, timeout_seconds: int) -> list[dict[str, Any]]:
        query = self._parse_provider_url(provider_url)
        search_url = self._build_search_url(query)
        raw_data = self._fetch_json(search_url, timeout_seconds=timeout_seconds)

        results = raw_data.get("results", []) if isinstance(raw_data, dict) else []
        if not isinstance(results, list):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mercado Libre API response did not contain a results array.",
            )

        items: list[dict[str, Any]] = []
        site_id = query["site_id"]
        for item in results:
            if not isinstance(item, dict):
                continue
            item["_discount_hub_site_id"] = site_id
            item["_discount_hub_site_name"] = _SITE_NAMES.get(site_id, f"Mercado Libre {site_id}")
            item["_discount_hub_site_country"] = _SITE_COUNTRIES.get(site_id, site_id[-2:])
            item["_discount_hub_query"] = query["q"]
            items.append(item)

        return self._apply_local_quality_filters(items, query)

    def _parse_provider_url(self, provider_url: str) -> dict[str, str]:
        value = provider_url.strip()
        if not value.startswith("mercadolibre://search"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mercado Libre providers must use mercadolibre://search?... URL format.",
            )

        parsed = urllib.parse.urlparse(value)
        params = urllib.parse.parse_qs(parsed.query)

        site_id = (self._single(params, "site_id") or "MLM").upper()
        if site_id not in _SITE_NAMES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Unsupported Mercado Libre site_id. Use one of: "
                    + ", ".join(sorted(_SITE_NAMES.keys()))
                ),
            )

        q = self._single(params, "q") or "ofertas"
        limit = self._clamp_int(self._single(params, "limit"), default=50, minimum=1, maximum=50)
        offset = self._clamp_int(self._single(params, "offset"), default=0, minimum=0, maximum=950)
        sort = self._single(params, "sort") or ""
        category = self._single(params, "category") or ""

        min_price = self._single(params, "min_price") or ""
        min_discount = self._single(params, "min_discount") or ""
        discount_only = self._single(params, "discount_only") or "false"
        free_shipping = self._single(params, "free_shipping") or "false"
        exclude_keywords = self._single(params, "exclude_keywords") or ""

        return {
            "site_id": site_id,
            "q": q[:100],
            "limit": str(limit),
            "offset": str(offset),
            "sort": sort[:60],
            "category": category[:40],
            "min_price": min_price,
            "min_discount": min_discount,
            "discount_only": discount_only.lower(),
            "free_shipping": free_shipping.lower(),
            "exclude_keywords": exclude_keywords,
        }

    def _build_search_url(self, query: dict[str, str]) -> str:
        params: dict[str, str] = {
            "q": query["q"],
            "limit": query["limit"],
            "offset": query["offset"],
        }
        if query["sort"]:
            params["sort"] = query["sort"]
        if query["category"]:
            params["category"] = query["category"]
        if query["free_shipping"] in {"true", "1", "yes"}:
            params["shipping_cost"] = "free"

        return (
            f"https://api.mercadolibre.com/sites/{urllib.parse.quote(query['site_id'])}/search?"
            f"{urllib.parse.urlencode(params)}"
        )

    def _apply_local_quality_filters(
        self,
        items: list[dict[str, Any]],
        query: dict[str, str],
    ) -> list[dict[str, Any]]:
        min_price = self._parse_float(query.get("min_price", ""))
        min_discount = self._parse_float(query.get("min_discount", ""))
        discount_only = query.get("discount_only", "false") in {"true", "1", "yes"}
        exclude_keywords = [
            keyword.strip().lower()
            for keyword in query.get("exclude_keywords", "").split("|")
            if keyword.strip()
        ]

        filtered: list[dict[str, Any]] = []
        for item in items:
            title = str(item.get("title") or "").lower()
            searchable_text = title

            if exclude_keywords and any(keyword in searchable_text for keyword in exclude_keywords):
                continue

            price = self._number(item.get("price"))
            if min_price is not None and price is not None and price < min_price:
                continue

            discount = self._discount_percent(item)
            if discount_only and discount is None:
                continue
            if min_discount is not None and (discount is None or discount < min_discount):
                continue

            filtered.append(item)
        return filtered

    def _discount_percent(self, item: dict[str, Any]) -> float | None:
        current_price = self._number(item.get("price"))
        original_price = self._number(item.get("original_price"))
        base_price = self._number(item.get("base_price"))

        old_price = original_price if original_price and original_price > 0 else base_price
        if current_price is None or old_price is None or old_price <= current_price or old_price <= 0:
            return None
        return ((old_price - current_price) / old_price) * 100

    def _fetch_json(self, url: str, *, timeout_seconds: int) -> Any:
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "DiscountHub-MercadoLibre-Adapter/0.1",
                },
            )
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                raw_body = response.read().decode(charset, errors="replace")
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mercado Libre API returned HTTP {exc.code}: {error_body[:500]}",
            ) from exc
        except urllib.error.URLError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not reach Mercado Libre API: {exc}",
            ) from exc

        try:
            return json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mercado Libre API did not return valid JSON: {exc}",
            ) from exc

    def _single(self, params: dict[str, list[str]], key: str) -> str | None:
        values = params.get(key)
        if not values:
            return None
        value = values[0].strip()
        return value or None

    def _clamp_int(self, value: str | None, *, default: int, minimum: int, maximum: int) -> int:
        try:
            parsed = int(str(value or "").strip())
        except ValueError:
            parsed = default
        return min(max(parsed, minimum), maximum)

    def _parse_float(self, value: str) -> float | None:
        text = str(value or "").strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None

    def _number(self, value: Any) -> float | None:
        if value is None or value == "":
            return None
        if isinstance(value, int | float):
            return float(value)
        try:
            return float(str(value).replace(",", "").strip())
        except ValueError:
            return None


mercadolibre_service = MercadoLibreService()
