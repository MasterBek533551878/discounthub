from __future__ import annotations

import base64
import json
import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class AdmitadDeeplinkService:
    """Build Admitad product-level deeplinks without touching Awin/eBay.

    DiscountHub imports product feeds from many Admitad programs. Some feeds expose
    a default tracking URL in `gotolink` and a product URL in another column. A
    default tracking URL can land on the merchant homepage; product-level traffic
    needs a deeplink. For reliability we try Admitad's official Deeplink Generator
    API on click and fall back to a local `ulp` deeplink template.
    """

    _TRACKING_DOMAINS = ("rzekl.com", "rztekl.com", "ad.admitad.com")
    _TOKEN_SCOPE = "advcampaigns advcampaigns_for_website websites deeplink_generator"

    def __init__(self) -> None:
        self._token_value: str | None = None
        self._token_expires_at: float = 0
        self._link_cache: dict[tuple[str, str], tuple[float, str]] = {}
        self._cache_ttl_seconds = 60 * 60 * 6

    def build_click_target(
        self,
        *,
        provider_id: str | None,
        affiliate_url: str | None,
        product_url: str | None,
    ) -> str | None:
        """Return a product deeplink for an Admitad deal.

        This is intentionally scoped to Admitad only. It returns None for eBay,
        Awin, direct deals, and all non-Admitad URLs.
        """
        if not self._looks_like_admitad(provider_id=provider_id, affiliate_url=affiliate_url):
            return None

        target_url = self.extract_target_url(product_url) or self.extract_target_url(affiliate_url)
        if not target_url:
            return self.build_manual_deeplink(affiliate_url, product_url)

        campaign_id = self.extract_campaign_id(provider_id)
        if campaign_id:
            generated = self.generate_with_api(campaign_id=campaign_id, target_url=target_url)
            if generated:
                return generated

        return self.build_manual_deeplink(affiliate_url, target_url)

    def extract_campaign_id(self, provider_id: str | None) -> str | None:
        if not provider_id:
            return None
        match = re.match(r"^admitad_(\d+)(?:_|$)", str(provider_id).strip())
        if not match:
            return None
        return match.group(1)

    def generate_with_api(self, *, campaign_id: str, target_url: str) -> str | None:
        settings = get_settings()
        website_id = settings.admitad_website_id.strip()
        if not website_id or not settings.admitad_client_id.strip() or not settings.admitad_client_secret.strip():
            return None

        normalized_target = self.extract_target_url(target_url) or target_url.strip()
        if not normalized_target:
            return None

        cache_key = (str(campaign_id), normalized_target)
        now = time.time()
        cached = self._link_cache.get(cache_key)
        if cached and cached[0] > now:
            return cached[1]

        token = self._get_access_token()
        if not token:
            return None

        api_base = settings.admitad_api_base_url.strip().rstrip("/") or "https://api.admitad.com"
        query = urllib.parse.urlencode({"ulp": normalized_target})
        url = f"{api_base}/deeplink/{urllib.parse.quote(website_id)}/advcampaign/{urllib.parse.quote(str(campaign_id))}/?{query}"
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
                "User-Agent": "DiscountHub-Admitad-Deeplink/0.1",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                raw_body = response.read().decode(response.headers.get_content_charset() or "utf-8", errors="replace")
        except Exception as exc:  # pragma: no cover - network/provider defensive fallback.
            logger.warning("Admitad deeplink generator failed for campaign %s: %s", campaign_id, exc)
            return None

        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            logger.warning("Admitad deeplink generator returned non-JSON response for campaign %s", campaign_id)
            return None

        link = self._extract_deeplink_from_payload(payload)
        if not link:
            return None

        self._link_cache[cache_key] = (now + self._cache_ttl_seconds, link)
        return link

    def build_manual_deeplink(self, base_url: str | None, product_url: str | None) -> str | None:
        if not base_url:
            return self.extract_target_url(product_url) or self._clean_url(product_url)

        cleaned_base = base_url.strip()
        if not self.is_admitad_tracking_url(cleaned_base):
            return cleaned_base

        target = self.extract_target_url(product_url) or self.extract_target_url(cleaned_base)
        if not target:
            return cleaned_base

        parsed = urllib.parse.urlparse(cleaned_base)
        params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        params["ulp"] = [target]
        query = urllib.parse.urlencode(params, doseq=True)
        scheme = parsed.scheme if parsed.scheme in {"http", "https"} else "https"
        path = parsed.path or "/"

        # Preserve the original Admitad tracking host/path from the feed. Some
        # programs use shortened tracking domains such as rzekl.com; rewriting
        # every link to ad.admitad.com can change provider-specific routing.
        return urllib.parse.urlunparse((scheme, parsed.netloc, path, "", query, ""))

    def extract_target_url(self, value: str | None) -> str | None:
        """Extract the real merchant target URL from product/deeplink fields.

        Works for AliExpress (`dl_target_url`), Admitad (`ulp`), and generic feed
        fields. Unlike the old helper, this is not AliExpress-only, so future
        Admitad programs can use the same safe path.
        """
        if not value:
            return None

        candidates = [value.strip()]
        current = value.strip()
        for _ in range(5):
            decoded = urllib.parse.unquote(current)
            if decoded == current:
                break
            candidates.append(decoded)
            current = decoded

        for candidate in candidates:
            parsed = urllib.parse.urlparse(candidate)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                continue

            params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
            for key in (
                "dl_target_url",
                "target_url",
                "merchant_url",
                "product_url",
                "url",
                "u",
                "ulp",
            ):
                for nested in params.get(key, []):
                    nested_target = self.extract_target_url(nested)
                    if nested_target:
                        return nested_target

            if not self.is_admitad_tracking_url(candidate):
                return self._strip_url_noise(candidate)

        return None

    def is_admitad_tracking_url(self, url: str | None) -> bool:
        if not url:
            return False
        parsed = urllib.parse.urlparse(url.strip())
        host = parsed.netloc.lower()
        return any(domain in host for domain in self._TRACKING_DOMAINS)

    def _looks_like_admitad(self, *, provider_id: str | None, affiliate_url: str | None) -> bool:
        if provider_id and str(provider_id).startswith("admitad_"):
            return True
        return self.is_admitad_tracking_url(affiliate_url)

    def _get_access_token(self) -> str | None:
        now = time.time()
        if self._token_value and self._token_expires_at > now + 60:
            return self._token_value

        settings = get_settings()
        client_id = settings.admitad_client_id.strip()
        client_secret = settings.admitad_client_secret.strip()
        api_base = settings.admitad_api_base_url.strip().rstrip("/") or "https://api.admitad.com"
        if not client_id or not client_secret:
            return None

        basic = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
        body = urllib.parse.urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": client_id,
                "scope": self._TOKEN_SCOPE,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{api_base}/token/",
            data=body,
            method="POST",
            headers={
                "Accept": "application/json",
                "Authorization": f"Basic {basic}",
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                "User-Agent": "DiscountHub-Admitad-Deeplink/0.1",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                payload = json.loads(response.read().decode(response.headers.get_content_charset() or "utf-8", errors="replace"))
        except Exception as exc:  # pragma: no cover - network/provider defensive fallback.
            logger.warning("Admitad token request failed for deeplink generator: %s", exc)
            return None

        token = str(payload.get("access_token") or "").strip()
        if not token:
            return None

        try:
            expires_in = int(float(payload.get("expires_in") or 3600))
        except (TypeError, ValueError):
            expires_in = 3600

        self._token_value = token
        self._token_expires_at = now + max(300, expires_in - 120)
        return token

    def _extract_deeplink_from_payload(self, payload: Any) -> str | None:
        for value in self._walk_values(payload):
            if not isinstance(value, str):
                continue
            text = value.strip()
            if not text.startswith(("http://", "https://")):
                continue
            if self.is_admitad_tracking_url(text):
                return text
        return None

    def _walk_values(self, value: Any) -> list[Any]:
        if isinstance(value, dict):
            preferred: list[Any] = []
            for key in ("deeplink", "link", "url", "tracking_link", "tracking_url", "gotolink", "short_link"):
                if key in value:
                    preferred.append(value[key])
            for key, child in value.items():
                if key not in {"deeplink", "link", "url", "tracking_link", "tracking_url", "gotolink", "short_link"}:
                    preferred.extend(self._walk_values(child))
            return preferred
        if isinstance(value, list):
            result: list[Any] = []
            for child in value:
                result.extend(self._walk_values(child))
            return result
        return [value]

    def _strip_url_noise(self, url: str) -> str:
        parsed = urllib.parse.urlparse(url.strip())
        if "aliexpress." in parsed.netloc.lower() and "/item/" in parsed.path:
            # Keep AliExpress item links stable. Query parameters from product
            # feeds are often tracking/noise and can break mobile redirects.
            return urllib.parse.urlunparse(parsed._replace(query="", fragment=""))
        return urllib.parse.urlunparse(parsed._replace(fragment=""))

    def _clean_url(self, value: str | None) -> str | None:
        if not value:
            return None
        cleaned = value.strip()
        return cleaned or None


admitad_deeplink_service = AdmitadDeeplinkService()
