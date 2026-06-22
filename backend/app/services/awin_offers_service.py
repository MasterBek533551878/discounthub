from __future__ import annotations

import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.models.promotion import AwinPromotionSyncRequest, PromotionUpsertRequest


class AwinOffersService:
    """Imports Awin My Offers promotions/vouchers into DiscountHub promotions.

    This is intentionally separate from Awin product-feed import:
    - product feeds create concrete product discount cards in /deals;
    - Offers API creates store-level promo/voucher cards in /promotions.
    """

    def fetch_promotions(self, request: AwinPromotionSyncRequest) -> tuple[list[PromotionUpsertRequest], int, int]:
        settings = get_settings()
        publisher_id = settings.awin_publisher_id.strip()
        access_token = (settings.awin_api_access_token or settings.awin_datafeed_api_key).strip()

        if not publisher_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="AWIN_PUBLISHER_ID is not configured in backend/.env.",
            )
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="AWIN_API_ACCESS_TOKEN or AWIN_DATAFEED_API_KEY is not configured in backend/.env.",
            )

        endpoint = self._offers_endpoint(settings.awin_api_base_url, publisher_id, access_token)
        promotions: list[PromotionUpsertRequest] = []
        skipped = 0
        pages_checked = 0

        for page in range(1, request.max_pages + 1):
            pages_checked = page
            body = self._build_body(request, page=page)
            response = self._post_json(endpoint, body=body, access_token=access_token)
            items = self._extract_items(response)
            if not items:
                break

            for item in items:
                promo = self._item_to_promotion(item)
                if promo is None:
                    skipped += 1
                    continue
                promotions.append(promo)

            if len(items) < request.page_size:
                break

        return promotions, skipped, pages_checked

    def _offers_endpoint(self, base_url: str, publisher_id: str, access_token: str) -> str:
        base = base_url.strip().rstrip("/") or "https://api.awin.com"
        query = urllib.parse.urlencode({"accessToken": access_token})
        return f"{base}/publisher/{urllib.parse.quote(str(publisher_id))}/promotions?{query}"

    def _build_body(self, request: AwinPromotionSyncRequest, *, page: int) -> dict[str, Any]:
        filters: dict[str, Any] = {
            "membership": request.membership,
            "status": request.status,
            "type": request.type,
        }
        if request.advertiser_ids:
            filters["advertiserIds"] = request.advertiser_ids
        if request.region_codes:
            filters["regionCodes"] = [code.strip().upper() for code in request.region_codes if code.strip()]
        if request.exclusive_only is not None:
            filters["exclusiveOnly"] = request.exclusive_only
        if request.updated_since:
            filters["updatedSince"] = request.updated_since.strip()

        return {
            "filters": filters,
            "pagination": {
                "page": page,
                "pageSize": request.page_size,
            },
        }

    def _post_json(self, url: str, *, body: dict[str, Any], access_token: str) -> Any:
        data = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": access_token,
                "User-Agent": "DiscountHub/0.1 AwinOffersImporter",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8-sig", errors="replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1200]
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Awin Offers API returned HTTP {exc.code}: {detail}",
            ) from exc
        except urllib.error.URLError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Awin Offers API connection failed: {exc}",
            ) from exc

        try:
            return json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Awin Offers API returned non-JSON response: {raw[:800]}",
            ) from exc

    def _extract_items(self, response: Any) -> list[dict[str, Any]]:
        if isinstance(response, list):
            return [item for item in response if isinstance(item, dict)]
        if not isinstance(response, dict):
            return []

        for key in ("offers", "promotions", "data", "items", "results"):
            value = response.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
            if isinstance(value, dict):
                nested = self._extract_items(value)
                if nested:
                    return nested

        # Some Awin responses are a JSON object keyed by offer IDs.
        dict_values = [value for value in response.values() if isinstance(value, dict)]
        if dict_values and all("promotionId" in item or "id" in item for item in dict_values):
            return dict_values
        return []

    def _item_to_promotion(self, item: dict[str, Any]) -> PromotionUpsertRequest | None:
        promotion_id = self._first_value(item, "promotionId", "promotion_id", "id")
        if promotion_id is None or str(promotion_id).strip() == "":
            return None

        advertiser = item.get("advertiser") if isinstance(item.get("advertiser"), dict) else {}
        advertiser_id = self._first_value(advertiser, "id", "advertiserId", "advertiser_id")
        advertiser_name = self._first_string(advertiser, "name", "advertiserName", "advertiser_name")
        store = advertiser_name or self._first_string(item, "advertiserName", "merchantName", "store") or "Awin"

        raw_type = (self._first_string(item, "type") or "promotion").strip().lower()
        voucher = item.get("voucher") if isinstance(item.get("voucher"), dict) else {}
        code = self._first_string(voucher, "code") or self._first_string(item, "code", "voucherCode", "voucher_code")
        promo_type = "coupon" if raw_type == "voucher" or code else "sale"

        title = self._first_string(item, "title", "name") or "Store promotion"
        description = self._first_string(item, "description", "terms") or ""
        terms = self._first_string(item, "terms") or ""
        if terms and terms not in description:
            description = f"{description}\n\nTerms: {terms}".strip()

        if promo_type == "sale" and self._looks_urgent(title, description):
            promo_type = "flash_sale"

        landing_url = self._first_string(item, "url", "landingUrl", "landing_url", "destinationUrl", "destination_url")
        affiliate_url = self._first_string(item, "urlTracking", "trackingUrl", "tracking_url", "affiliateUrl", "affiliate_url")
        affiliate_url = self._repair_tracking_url(
            affiliate_url=affiliate_url,
            landing_url=landing_url,
            advertiser_id=advertiser_id,
        )
        image_url = self._first_url(
            item,
            "imageUrl",
            "image_url",
            "image",
            "thumbnailUrl",
            "thumbnail_url",
            "bannerUrl",
            "banner_url",
            "creativeUrl",
            "creative_url",
            "logoUrl",
            "logo_url",
        ) or self._first_url(
            advertiser,
            "imageUrl",
            "image_url",
            "logoUrl",
            "logo_url",
            "logo",
        )
        target_url = affiliate_url or landing_url
        if not target_url:
            return None

        start_date = self._parse_datetime(self._first_string(item, "startDate", "start_date", "validFrom", "valid_from"))
        end_date = self._parse_datetime(self._first_string(item, "endDate", "end_date", "validUntil", "valid_until"))
        added_date = self._parse_datetime(self._first_string(item, "dateAdded", "date_added", "updatedAt", "updated_at"))
        now = datetime.now(timezone.utc)
        if end_date is not None and end_date < now:
            return None

        discount_text = self._clean_text(self._extract_discount_text(title, description))
        if self._is_low_value_non_discount_offer(
            title=title,
            description=description,
            promo_type=promo_type,
            code=code,
            extracted_discount_text=discount_text,
        ):
            return None
        if not discount_text:
            discount_text = "Promo code" if promo_type == "coupon" else "Sale"

        featured = promo_type == "coupon" or self._discount_number(discount_text) >= 30
        provider_suffix = str(advertiser_id).strip() if advertiser_id is not None and str(advertiser_id).strip() else "unknown"

        return PromotionUpsertRequest(
            id=f"awin:{promotion_id}",
            type=promo_type,
            title=self._clean_text(title).strip(),
            description=self._clean_text(description).strip(),
            store=self._clean_text(store).strip(),
            discount_text=self._clean_text(discount_text).strip(),
            code=self._clean_text(code).strip() if code else None,
            landing_url=landing_url or target_url,
            affiliate_url=affiliate_url,
            image_url=image_url,
            provider_id=f"awin_offers_{provider_suffix}",
            monetization_mode="affiliate",
            valid_from=start_date,
            valid_until=end_date,
            featured=featured,
            updated_at=added_date or now,
        )

    def _repair_tracking_url(
        self,
        *,
        affiliate_url: str | None,
        landing_url: str | None,
        advertiser_id: Any,
    ) -> str | None:
        landing = (landing_url or "").strip()
        raw_affiliate = (affiliate_url or "").strip()
        advertiser = str(advertiser_id or "").strip()
        publisher = get_settings().awin_publisher_id.strip()

        if raw_affiliate:
            parsed = urllib.parse.urlparse(raw_affiliate)
            if "awin1.com" not in parsed.netloc.lower():
                return raw_affiliate

            params = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
            existing_ued = (params.get("ued") or "").strip()
            if existing_ued and not self._looks_like_generic_store_url(existing_ued):
                return raw_affiliate
            if not landing:
                return raw_affiliate

            params["ued"] = landing
            if advertiser and advertiser.isdigit() and not params.get("awinmid"):
                params["awinmid"] = advertiser
            if publisher and not params.get("awinaffid"):
                params["awinaffid"] = publisher
            return urllib.parse.urlunparse(
                parsed._replace(query=urllib.parse.urlencode(params, doseq=True))
            )

        if advertiser and advertiser.isdigit() and publisher and landing:
            query = urllib.parse.urlencode(
                {
                    "awinmid": advertiser,
                    "awinaffid": publisher,
                    "ued": landing,
                }
            )
            return f"https://www.awin1.com/cread.php?{query}"

        return raw_affiliate or None

    def _looks_like_generic_store_url(self, url: str) -> bool:
        parsed = urllib.parse.urlparse(urllib.parse.unquote(str(url or "")))
        host = parsed.netloc.lower()
        path = parsed.path.strip("/").lower()
        if not host:
            return True
        return path in {"", "/"} and any(
            domain in host for domain in ("alibaba.com", "aliexpress.com")
        )

    def _first_value(self, data: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            if key in data and data[key] is not None:
                return data[key]
        lowered = {str(key).lower(): value for key, value in data.items()}
        for key in keys:
            value = lowered.get(key.lower())
            if value is not None:
                return value
        return None

    def _first_string(self, data: dict[str, Any], *keys: str) -> str | None:
        value = self._first_value(data, *keys)
        if value is None:
            return None
        text = self._clean_text(str(value))
        return text or None

    def _first_url(self, data: dict[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = self._first_value(data, key)
            if isinstance(value, dict):
                nested = self._first_url(value, "url", "href", "src")
                if nested:
                    return nested
            if value is None:
                continue
            text = html.unescape(str(value)).strip()
            if text.startswith(("http://", "https://")):
                return text
        return None

    def _replace_mojibake_symbols(self, text: str) -> str:
        euro = chr(0x20AC)
        pound = chr(0x00A3)
        c2 = chr(0x00C2)
        e2 = chr(0x00E2)
        ac = chr(0x00AC)
        replacements = {
            e2 + chr(0x0082) + ac: euro,
            e2 + chr(0x201A) + ac: euro,
            e2 + chr(0x20AC) + chr(0x0161) + ac: euro,
            e2 + ac: euro,
            "â‚¬": euro,
            "â¬": euro,
            c2 + chr(0x00A3): pound,
            "Â£": pound,
            c2 + "$": "$",
            "Â$": "$",
            c2 + chr(0x00A0): " ",
            c2 + " ": " ",
            chr(0xFEFF): "",
            chr(0xFFFD): "",
        }
        for bad, good in replacements.items():
            text = text.replace(bad, good)
        text = re.sub(r"(\d)([€£$])(?=\s*(?:off|OFF|for|FOR|$))", r"\1\2 ", text)
        return re.sub(r"[ \t]+", " ", text).strip()

    def _clean_text(self, value: str) -> str:
        text = self._replace_mojibake_symbols(html.unescape(value).strip())
        if not text:
            return ""

        # Some Awin offers arrive as mojibake, for example
        # "Letnia WyprzedaÅ¼" instead of "Letnia Wyprzedaż" or
        # "â‚¬200 OFF" instead of "€200 OFF". Keep this repair narrow
        # so already-correct UTF-8 text is left untouched.
        mojibake_markers = ("Ã", "Å", "â", "Â", "ï¼")
        for _ in range(2):
            if not any(marker in text for marker in mojibake_markers):
                break
            repaired = None
            for encoding in ("latin1", "cp1252"):
                try:
                    candidate = text.encode(encoding).decode("utf-8")
                except UnicodeError:
                    continue
                if candidate and candidate != text:
                    repaired = candidate
                    break
            if repaired is None:
                break
            text = self._replace_mojibake_symbols(repaired)

        text = self._replace_mojibake_symbols(text)

        replacements = {
            "â‚¬": "€",
            "â¬": "€",
            "Â£": "£",
            "Â$": "$",
            "ï¼š": ":",
            "ï¼": ":",
            "：": ":",
            "￡": "£",
            "￥": "¥",
            " ": " ",
            # Common AliExpress PL offer labels. These often arrive either
            # in Polish or as partly-corrupted Polish mojibake. Keep them
            # user-facing and English for the current app UI.
            "Letnia Wyprzedaż": "Summer Sale",
            "Letnia WyprzedaÅ": "Summer Sale",
            "Wartość": "Value",
            "WartoÅ": "Value",
            "Min. Zamówienie": "Min. order",
            "Min. ZamÃ³wienie": "Min. order",
        }
        for bad, good in replacements.items():
            text = text.replace(bad, good)
        return re.sub(r"[ \t]+", " ", text).strip()

    def _is_low_value_non_discount_offer(
        self,
        *,
        title: str,
        description: str,
        promo_type: str,
        code: str | None,
        extracted_discount_text: str,
    ) -> bool:
        cleaned_title = self._clean_text(title)
        cleaned_description = self._clean_text(description)
        cleaned_discount = self._clean_text(extracted_discount_text)
        text = f"{cleaned_title} {cleaned_description} {cleaned_discount}".lower()

        # DiscountHub promotion tab should contain actual coupons/sales, not
        # generic service announcements, free-delivery messages, gifts, bundles
        # or marketplace marketing claims that are not a user-actionable deal.
        hard_block_terms = (
            "free shipping",
            "free delivery",
            "free mainland uk delivery",
            "free uk delivery",
            "free gift",
            "gift with purchase",
            "buy one get one",
            "bogo",
            "2 for 1",
            "3 for 2",
            "alibaba lens",
            "one image search",
            "image search for price comparison",
            "saving spotlight",
            "below retail price",
            "ai & app subscription",
            "ai & app subspriction",
        )
        if any(term in text for term in hard_block_terms):
            return True

        def has_concrete_discount(value: str) -> bool:
            value = self._clean_text(value).lower()
            if code:
                return True
            if re.search(r"\b\d{1,3}\s*%\s*(?:off|discount)?\b", value):
                return True
            if re.search(r"(?:[€£$]\s*\d+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?\s*[€£$])\s*(?:off|discount|save)?\b", value):
                return True
            if re.search(r"\b(?:save|get)\s+(?:up\s+to\s+)?(?:[€£$]\s*\d+|\d+\s*[€£$]|\d{1,3}\s*%)", value):
                return True
            return False

        generic_discount = cleaned_discount.lower().strip() in ("", "sale", "promo code", "promotion", "offer")
        if promo_type != "coupon" and not code and generic_discount:
            return not has_concrete_discount(f"{cleaned_title} {cleaned_description}")

        return False

    def _parse_datetime(self, value: str | None) -> datetime | None:
        if not value:
            return None
        raw = value.strip()
        if not raw:
            return None
        for candidate in (raw, raw.replace("Z", "+00:00")):
            try:
                parsed = datetime.fromisoformat(candidate)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed.astimezone(timezone.utc)
            except ValueError:
                continue
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
            try:
                return datetime.fromisoformat(raw).replace(tzinfo=timezone.utc)
            except ValueError:
                return None
        return None

    def _looks_urgent(self, title: str, description: str) -> bool:
        text = f"{title} {description}".lower()
        urgent_terms = (
            "flash",
            "today only",
            "24h",
            "24 hour",
            "48h",
            "48 hour",
            "limited time",
            "ends today",
            "ends tonight",
            "weekend sale",
            "cyber monday",
            "black friday",
        )
        return any(term in text for term in urgent_terms)

    def _extract_discount_text(self, title: str, description: str) -> str:
        text = " ".join(part for part in [title, description] if part).replace("\n", " ")
        patterns = [
            r"(?:up\s*to\s*)?\d{1,3}\s*%\s*(?:off|discount|sale)?",
            r"(?:save|get)\s*(?:up\s*to\s*)?\d{1,3}\s*%",
            r"(?:save|get)\s*(?:up\s*to\s*)?[€£$]\s*\d+(?:[.,]\d{1,2})?",
            r"[€£$]\s*\d+(?:[.,]\d{1,2})?\s*off",
            r"(?:up\s*to\s*)?\d{1,3}\s*%",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return re.sub(r"\s+", " ", match.group(0)).strip()
        return ""

    def _discount_number(self, discount_text: str) -> int:
        match = re.search(r"(\d{1,3})\s*%", discount_text)
        if not match:
            return 0
        try:
            return max(0, min(100, int(match.group(1))))
        except ValueError:
            return 0


awin_offers_service = AwinOffersService()
