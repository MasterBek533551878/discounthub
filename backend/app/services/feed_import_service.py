import csv
import gzip
import io
import itertools
import json
import re
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

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
        feed_url, local_options = self._split_local_feed_options(feed_url)
        max_items = self._optional_positive_int(local_options.get("max_items"))
        max_scan_rows = self._optional_positive_int(local_options.get("max_scan_rows"))
        min_discount_percent = self._optional_float(local_options.get("min_discount_percent"))
        platform_name = self._optional_clean_string(local_options.get("platform_name"))

        if adapter == "admitad_products":
            # Admitad CSV product feeds can be very large. Keep syncs bounded by
            # default, even when older DB rows do not yet include local options.
            if max_items is None:
                max_items = 2000
            if max_scan_rows is None:
                max_scan_rows = max(max_items * 20, 25000)
            if min_discount_percent is None:
                min_discount_percent = 10

        if adapter == "ebay_browse_api":
            if not feed_url.startswith("ebay://browse"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="eBay Browse providers must use ebay://browse?... URLs.",
                )
        elif adapter == "awin_feed_list_api":
            if not feed_url.startswith(("awin://feed-list", "http://", "https://")):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Awin feed-list providers must use awin://feed-list?... or a full https:// feed-list URL.",
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
        elif adapter == "awin_feed_list_api":
            # Runtime import avoids a module cycle: Awin feed-list expansion uses
            # the same CSV/JSON parsing ideas but returns normal awin_products rows.
            from app.services.awin_feed_list_service import awin_feed_list_service

            raw_items = awin_feed_list_service.search_from_provider_url(
                feed_url,
                timeout_seconds=timeout_seconds,
            )
            adapter = "awin_products"
        elif adapter == "admitad_products":
            raw_items = self._fetch_csv_items_streaming(
                feed_url,
                timeout_seconds=timeout_seconds,
                max_items=max_items,
                max_scan_rows=max_scan_rows,
                min_discount_percent=min_discount_percent,
            )
            if platform_name:
                for item in raw_items:
                    item.setdefault("_discounthub_platform_name", platform_name)
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


    def _split_local_feed_options(self, feed_url: str) -> tuple[str, dict[str, str]]:
        """Read DiscountHub-only feed controls without sending them upstream.

        Local options may be placed either in the query string or URL fragment,
        for example: #discounthub_max_items=2000&discounthub_min_discount_percent=10
        They are removed before urllib opens the remote URL.
        """
        parts = urlsplit(feed_url)
        options: dict[str, str] = {}

        def split_pairs(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
            kept: list[tuple[str, str]] = []
            for key, value in pairs:
                normalized_key = key.strip().lower()
                if normalized_key.startswith("discounthub_"):
                    options[normalized_key.removeprefix("discounthub_")] = value
                else:
                    kept.append((key, value))
            return kept

        query_pairs = split_pairs(parse_qsl(parts.query, keep_blank_values=True))

        fragment = parts.fragment
        kept_fragment = fragment
        if "discounthub_" in fragment and "=" in fragment:
            fragment_pairs = split_pairs(parse_qsl(fragment, keep_blank_values=True))
            kept_fragment = urlencode(fragment_pairs, doseq=True)

        cleaned_url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query_pairs, doseq=True), kept_fragment))
        return cleaned_url, options

    def _optional_positive_int(self, value: str | None) -> int | None:
        if value is None or str(value).strip() == "":
            return None
        try:
            number = int(float(str(value).strip()))
        except ValueError:
            return None
        return number if number > 0 else None

    def _optional_float(self, value: str | None) -> float | None:
        if value is None or str(value).strip() == "":
            return None
        try:
            return float(str(value).strip().replace(",", "."))
        except ValueError:
            return None

    def _optional_clean_string(self, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    def _fetch_csv_items_streaming(
        self,
        feed_url: str,
        *,
        timeout_seconds: int,
        max_items: int | None = None,
        max_scan_rows: int | None = None,
        min_discount_percent: float | None = None,
    ) -> list[dict[str, Any]]:
        try:
            request = urllib.request.Request(
                feed_url,
                headers={
                    "Accept": "text/csv,text/tab-separated-values,*/*",
                    "User-Agent": "DiscountHub-MVP-Importer/0.1",
                },
            )
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                content_type = (response.headers.get("content-type", "") or "").lower()
                charset = response.headers.get_content_charset() or "utf-8"
                content_encoding = (response.headers.get("content-encoding", "") or "").lower()
                raw_stream: Any = response
                if "gzip" in content_encoding or feed_url.lower().split("?")[0].endswith(".gz"):
                    raw_stream = gzip.GzipFile(fileobj=response)

                text_stream = io.TextIOWrapper(raw_stream, encoding=charset, errors="replace", newline="")
                return self._extract_csv_items_streaming(
                    text_stream,
                    feed_url=feed_url,
                    content_type=content_type,
                    max_items=max_items,
                    max_scan_rows=max_scan_rows,
                    min_discount_percent=min_discount_percent,
                )
        except urllib.error.URLError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not fetch feed URL: {exc}",
            ) from exc

    def _extract_csv_items_streaming(
        self,
        stream: Any,
        *,
        feed_url: str,
        content_type: str,
        max_items: int | None = None,
        max_scan_rows: int | None = None,
        min_discount_percent: float | None = None,
    ) -> list[dict[str, Any]]:
        sample_lines: list[str] = []
        for _ in range(25):
            line = stream.readline()
            if line == "":
                break
            sample_lines.append(line)

        if not sample_lines:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CSV feed did not contain any product rows.",
            )

        sample = "".join(sample_lines)
        delimiter = "\t" if (feed_url.lower().split("?")[0].endswith(".tsv") or "tab-separated" in content_type) else None
        if delimiter is None:
            try:
                delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
            except csv.Error:
                delimiter = ","

        reader = csv.DictReader(itertools.chain(sample_lines, stream), delimiter=delimiter)
        if not reader.fieldnames:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CSV feed must have a header row.",
            )

        normalized_headers = [str(header or "").strip() for header in reader.fieldnames]
        items: list[dict[str, Any]] = []
        scanned = 0
        skipped_by_discount = 0
        skipped_by_stock = 0
        for row in reader:
            scanned += 1
            if max_scan_rows is not None and scanned > max_scan_rows:
                break

            item = self._csv_row_to_item(row=row, normalized_headers=normalized_headers)
            if not item:
                continue

            if self._raw_is_out_of_stock(item):
                skipped_by_stock += 1
                continue

            if min_discount_percent is not None:
                discount = self._raw_discount_percent(item)
                if discount is None or discount < min_discount_percent:
                    skipped_by_discount += 1
                    continue

            items.append(item)
            if max_items is not None and len(items) >= max_items:
                break

        if not items:
            reason = "CSV feed did not contain any product rows."
            if min_discount_percent is not None:
                reason = (
                    "CSV feed was reachable, but no rows passed "
                    f"min discount {min_discount_percent:g}% within the first {scanned} scanned row(s)."
                )
            if skipped_by_stock:
                reason += f" Skipped {skipped_by_stock} explicit out-of-stock row(s)."
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason)

        return items

    def _csv_row_to_item(self, *, row: dict[str, Any], normalized_headers: list[str]) -> dict[str, Any]:
        item: dict[str, Any] = {}
        for raw_key, value in row.items():
            key = str(raw_key or "").strip()
            if not key:
                continue
            item[key] = value.strip() if isinstance(value, str) else value

        for header in normalized_headers:
            if not header or header not in item:
                continue
            normalized_key = self._normalize_header(header)
            item.setdefault(normalized_key, item[header])

        if any(value not in (None, "") for value in item.values()):
            return item
        return {}

    def _raw_discount_percent(self, item: dict[str, Any]) -> float | None:
        explicit = self._raw_number(
            item,
            "discount",
            "discount_percent",
            "discount_percentage",
            "saving_percent",
            "savings_percent",
        )
        if explicit is not None and explicit > 0:
            return explicit

        current = self._raw_number(item, "price", "sale_price", "current_price", "product_price", "search_price")
        old = self._raw_number(item, "oldprice", "old_price", "original_price", "rrp", "retail_price", "was_price")
        if current is None or old is None or old <= 0 or current <= 0 or old <= current:
            return None
        return ((old - current) / old) * 100

    def _raw_is_out_of_stock(self, item: dict[str, Any]) -> bool:
        stock_text = " ".join(
            str(item.get(key, "")).strip().lower()
            for key in (
                "availability",
                "g_availability",
                "g:availability",
                "stock",
                "stock_status",
                "availability_status",
                "status",
                "in_stock",
                "instock",
                "is_available",
                "available",
            )
            if item.get(key) not in (None, "")
        )
        if not stock_text:
            return False

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
        if any(marker in stock_text for marker in bad_markers):
            return True

        negative_exact = {"0", "0.0", "false", "no", "n", "off"}
        return stock_text in negative_exact

    def _raw_number(self, item: dict[str, Any], *keys: str) -> float | None:
        for key in keys:
            value = item.get(key)
            if value is None or value == "":
                continue
            if isinstance(value, int | float):
                return float(value)
            text = str(value).strip()
            match = re.search(r"[-+]?\d+(?:[\s,]\d{3})*(?:[.,]\d+)?|[-+]?\d+", text)
            if not match:
                continue
            number = match.group(0).replace(" ", "")
            if number.count(",") == 1 and number.count(".") == 0:
                number = number.replace(",", ".")
            else:
                number = number.replace(",", "")
            try:
                return float(number)
            except ValueError:
                continue
        return None

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
