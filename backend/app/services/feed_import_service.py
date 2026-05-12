import csv
import io
import json
import urllib.error
import urllib.request
from typing import Any

from fastapi import HTTPException, status
from pydantic import ValidationError

from app.models.deal import DealsImportRequest
from app.models.feed_provider import FeedProviderAdapter
from app.services.feed_adapters import feed_adapter_service
from app.services.ebay_browse_service import ebay_browse_service
from app.services.mercadolibre_service import mercadolibre_service


class FeedImportService:
    def build_import_request_from_url(
        self,
        *,
        url: str,
        adapter: FeedProviderAdapter = "auto",
        replace: bool = False,
        timeout_seconds: int = 20,
    ) -> DealsImportRequest:
        feed_url = url.strip()
        if adapter == "ebay_browse_api":
            if not feed_url.startswith("ebay://browse"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="eBay Browse providers must use ebay://browse?... URLs.",
                )
        elif adapter == "mercadolibre_search_api":
            if not feed_url.startswith("mercadolibre://search"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Mercado Libre providers must use mercadolibre://search?... URLs.",
                )
        elif not feed_url.startswith(("http://", "https://")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only http:// and https:// feed URLs are supported for feed providers.",
            )

        if adapter == "ebay_browse_api":
            raw_items = ebay_browse_service.search_from_provider_url(
                feed_url,
                timeout_seconds=timeout_seconds,
            )
        elif adapter == "mercadolibre_search_api":
            raw_items = mercadolibre_service.search_from_provider_url(
                feed_url,
                timeout_seconds=timeout_seconds,
            )
        else:
            raw_body, content_type = self._fetch_text(feed_url, timeout_seconds=timeout_seconds)
            raw_items = self._extract_items_from_body(
                raw_body,
                feed_url=feed_url,
                content_type=content_type,
            )

        normalized_items = feed_adapter_service.normalize_items(adapter=adapter, raw_items=raw_items)

        try:
            return DealsImportRequest(items=normalized_items, replace=replace)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=json.loads(exc.json()),
            ) from exc

    def _fetch_text(self, feed_url: str, *, timeout_seconds: int) -> tuple[str, str]:
        try:
            request = urllib.request.Request(
                feed_url,
                headers={
                    "Accept": "application/json,text/csv,text/tab-separated-values,*/*",
                    "User-Agent": "DiscountHub-MVP-Importer/0.1",
                },
            )
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                content_type = response.headers.get("content-type", "") or ""
                charset = response.headers.get_content_charset() or "utf-8"
                raw_body = response.read().decode(charset, errors="replace")
        except urllib.error.URLError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not fetch feed URL: {exc}",
            ) from exc

        return raw_body, content_type.lower()

    def _extract_items_from_body(
        self,
        raw_body: str,
        *,
        feed_url: str,
        content_type: str,
    ) -> list[dict[str, Any]]:
        stripped = raw_body.lstrip("\ufeff\n\r\t ")
        looks_like_json = stripped.startswith(("[", "{")) or "json" in content_type
        looks_like_tsv = feed_url.lower().split("?")[0].endswith(".tsv") or "tab-separated" in content_type
        looks_like_csv = feed_url.lower().split("?")[0].endswith(".csv") or "csv" in content_type

        if looks_like_json:
            try:
                raw_data = json.loads(raw_body)
                return self._extract_import_items(raw_data)
            except json.JSONDecodeError as exc:
                if not (looks_like_csv or looks_like_tsv):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Feed did not return valid JSON: {exc}",
                    ) from exc

        delimiter = "\t" if looks_like_tsv else None
        return self._extract_csv_items(raw_body, delimiter=delimiter)

    def _extract_import_items(self, raw_data: Any) -> list[dict[str, Any]]:
        if isinstance(raw_data, list):
            return self._validate_items(raw_data)

        if not isinstance(raw_data, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Feed JSON must be either an array of products or an object with items/deals/products/offers.",
            )

        candidates = [raw_data.get("items"), raw_data.get("deals"), raw_data.get("products"), raw_data.get("offers")]
        for candidate in candidates:
            if candidate is None:
                continue
            if isinstance(candidate, list):
                return self._validate_items(candidate)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Feed items/deals/products/offers field must be an array.",
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Feed JSON object must contain items, deals, products, or offers array.",
        )

    def _extract_csv_items(self, raw_body: str, *, delimiter: str | None = None) -> list[dict[str, Any]]:
        sample = raw_body[:4096]
        if delimiter is None:
            try:
                delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
            except csv.Error:
                delimiter = ","

        reader = csv.DictReader(io.StringIO(raw_body), delimiter=delimiter)
        if not reader.fieldnames:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CSV feed must have a header row.",
            )

        normalized_headers = [str(header or "").strip() for header in reader.fieldnames]
        items: list[dict[str, Any]] = []
        for row in reader:
            item: dict[str, Any] = {}
            for raw_key, value in row.items():
                key = str(raw_key or "").strip()
                if not key:
                    continue
                item[key] = value.strip() if isinstance(value, str) else value

            # Also expose normalized snake-ish aliases for messy affiliate feeds.
            for header in normalized_headers:
                if not header or header not in item:
                    continue
                normalized_key = self._normalize_header(header)
                item.setdefault(normalized_key, item[header])

            if any(value not in (None, "") for value in item.values()):
                items.append(item)

        if not items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CSV feed did not contain any product rows.",
            )
        return items

    def _validate_items(self, raw_items: list[Any]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for index, item in enumerate(raw_items):
            if not isinstance(item, dict):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Feed item at index {index} must be a JSON object.",
                )
            items.append(item)
        return items

    def _normalize_header(self, value: str) -> str:
        normalized = value.strip().replace("/", "_").replace("-", "_")
        normalized = "".join(char if char.isalnum() else "_" for char in normalized)
        while "__" in normalized:
            normalized = normalized.replace("__", "_")
        return normalized.strip("_").lower()


feed_import_service = FeedImportService()
