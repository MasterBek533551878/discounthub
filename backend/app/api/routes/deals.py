from datetime import datetime, timedelta, timezone
from typing import Annotated
import re
import urllib.parse

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from app.models.deal import (
    DealMonetizationMode,
    DealsFacetsResponse,
    DealsPage,
    DealResponse,
    DealSort,
)
from app.repositories.deals_repository import DealsRepository
from app.services.deals_service import DealNotFoundError, deals_service
from app.services.admitad_deeplink_service import admitad_deeplink_service

router = APIRouter(tags=["deals"])


def _safe_click_target_for_deal(deal: DealResponse) -> str | None:
    """Return the outbound URL the app should open for this deal.

    We intentionally decide per marketplace. Some providers give both a tracking
    link and a product link; using `affiliate_url or product_url` is not enough:
    - eBay may provide noisy/affiliate URLs that resolve to eBay "Sorry" pages,
      while the product URL still contains the real item id.
    - Admitad/AliExpress links need the Admitad tracking domain but a clean
      AliExpress item URL inside the `ulp` target.
    """
    platform = (deal.platform or "").lower()
    affiliate_url = (deal.affiliate_url or "").strip() or None
    product_url = (deal.product_url or "").strip() or None

    if "ebay" in platform:
        return (
            _canonical_ebay_item_url(product_url)
            or _canonical_ebay_item_url(affiliate_url)
            or product_url
            or affiliate_url
        )

    admitad_target = admitad_deeplink_service.build_click_target(
        provider_id=deal.provider_id,
        affiliate_url=affiliate_url,
        product_url=product_url,
    )
    if admitad_target:
        return admitad_target

    return _safe_click_target(affiliate_url) or _safe_click_target(product_url)


def _safe_click_target(raw_url: str | None) -> str | None:
    """Return a cleaner redirect target for a raw affiliate/product link."""
    if not raw_url:
        return None

    url = raw_url.strip()
    if not url:
        return None

    admitad_repaired = _repair_admitad_aliexpress_url(url)
    if admitad_repaired:
        return admitad_repaired

    ebay_repaired = _canonical_ebay_item_url(url)
    if ebay_repaired:
        return ebay_repaired

    return url


def _repair_admitad_aliexpress_url(url: str | None, *, product_url: str | None = None) -> str | None:
    if not admitad_deeplink_service.is_admitad_tracking_url(url):
        return None
    return admitad_deeplink_service.build_manual_deeplink(url, product_url)

def _extract_aliexpress_product_url(value: str) -> str | None:
    if not value:
        return None

    candidates = [value]
    current = value
    for _ in range(5):
        decoded = urllib.parse.unquote(current)
        if decoded == current:
            break
        candidates.append(decoded)
        current = decoded

    for candidate in candidates:
        parsed = urllib.parse.urlparse(candidate)
        host = parsed.netloc.lower()

        if "aliexpress." in host and "/item/" in parsed.path:
            return urllib.parse.urlunparse(parsed._replace(query="", fragment=""))

        nested_params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        for key in ("dl_target_url", "target_url", "url", "ulp"):
            for nested in nested_params.get(key, []):
                nested_result = _extract_aliexpress_product_url(nested)
                if nested_result:
                    return nested_result

        match = re.search(r"https?://(?:www\.)?aliexpress\.[^\s'\"<>]+/item/\d+\.html", candidate)
        if match:
            return match.group(0).split("?")[0]

    return None


def _canonical_ebay_item_url(url: str | None) -> str | None:
    if not url:
        return None

    parsed = urllib.parse.urlparse(url.strip())
    host = parsed.netloc.lower()
    if "ebay." not in host:
        return None

    # eBay URLs can be /itm/123, /itm/title/123, or embedded in query params.
    match = re.search(r"/itm/(?:[^/?#]+/)?(\d{6,})", parsed.path)
    if not match:
        decoded_url = urllib.parse.unquote(url)
        match = re.search(r"/itm/(?:[^/?#]+/)?(\d{6,})", decoded_url)
    if not match:
        return None

    item_id = match.group(1)

    # In browser tests, some regional eBay domains (notably ebay.co.uk, ebay.de,
    # ebay.it, ebay.fr and ebay.com.au) can show eBay's generic "Sorry" page
    # even when the same global item id opens correctly on ebay.com. Keep the
    # marketplaces in our UI/facets, but route clicks through the safer global
    # item page. eBay ES was verified as working, so we preserve it.
    host_without_www = host[4:] if host.startswith("www.") else host
    if host_without_www == "ebay.es":
        netloc = "www.ebay.es"
    else:
        netloc = "www.ebay.com"

    return urllib.parse.urlunparse(("https", netloc, f"/itm/{item_id}", "", "", ""))


def _deal_is_clickable_now(deal: DealResponse) -> bool:
    now = datetime.now(timezone.utc)
    if deal.expires_at is not None and deal.expires_at.astimezone(timezone.utc) < now:
        return False

    updated_at = deal.updated_at.astimezone(timezone.utc)
    platform = (deal.platform or "").lower()
    is_affiliate = deal.monetization_mode == "affiliate"
    if is_affiliate and "aliexpress" in platform:
        return updated_at >= now - timedelta(hours=48)
    if is_affiliate:
        return updated_at >= now - timedelta(days=7)
    return updated_at >= now - timedelta(hours=72)


@router.get("/deals", response_model=DealsPage, response_model_by_alias=True)
def list_deals(
    q: str | None = None,
    platform: str | None = None,
    category: str | None = None,
    ships_to: str | None = None,
    delivery_region: str | None = None,
    currency: str = "USD",
    min_discount: Annotated[int | None, Query(ge=0, le=100)] = None,
    min_rating: Annotated[float | None, Query(ge=0, le=5)] = None,
    max_price: Annotated[float | None, Query(gt=0)] = None,
    free_shipping: bool | None = None,
    verified: bool | None = None,
    monetization_mode: DealMonetizationMode | None = None,
    sort: DealSort = "score_desc",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DealsPage:
    items, total = deals_service.list_deals(
        q=q,
        platform=platform,
        category=category,
        ships_to=ships_to,
        delivery_region=delivery_region,
        currency=currency,
        min_discount=min_discount,
        min_rating=min_rating,
        max_price=max_price,
        free_shipping=free_shipping,
        verified=verified,
        monetization_mode=monetization_mode,
        sort=sort,
        page=page,
        page_size=page_size,
    )

    return DealsPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next_page=page * page_size < total,
    )


@router.get("/deals/facets", response_model=DealsFacetsResponse, response_model_by_alias=True)
def deal_facets(
    q: str | None = None,
    platform: str | None = None,
    category: str | None = None,
    ships_to: str | None = None,
    delivery_region: str | None = None,
    currency: str = "USD",
    min_discount: Annotated[int | None, Query(ge=0, le=100)] = None,
    min_rating: Annotated[float | None, Query(ge=0, le=5)] = None,
    max_price: Annotated[float | None, Query(gt=0)] = None,
    free_shipping: bool | None = None,
    verified: bool | None = None,
    monetization_mode: DealMonetizationMode | None = None,
) -> DealsFacetsResponse:
    return deals_service.get_facets(
        q=q,
        platform=platform,
        category=category,
        ships_to=ships_to,
        delivery_region=delivery_region,
        currency=currency,
        min_discount=min_discount,
        min_rating=min_rating,
        max_price=max_price,
        free_shipping=free_shipping,
        verified=verified,
        monetization_mode=monetization_mode,
    )


@router.get("/deals/{deal_id}/click", include_in_schema=True)
def click_deal(deal_id: str, request: Request) -> RedirectResponse:
    try:
        deal = deals_service.get_deal(deal_id, currency="USD")
    except DealNotFoundError:
        raise HTTPException(status_code=404, detail="Deal not found") from None

    if not _deal_is_clickable_now(deal):
        raise HTTPException(status_code=410, detail="Deal is no longer fresh enough to open")

    target_url = _safe_click_target_for_deal(deal)
    if not target_url:
        raise HTTPException(status_code=404, detail="Deal link not available")

    repository = DealsRepository()
    repository.record_click(
        deal_id=deal.id,
        platform=deal.platform,
        category=deal.category,
        provider_id=deal.provider_id,
        monetization_mode=deal.monetization_mode,
        target_url=target_url,
        referrer=request.headers.get("referer"),
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
        clicked_at=datetime.now(timezone.utc),
    )

    return RedirectResponse(url=target_url, status_code=302)


@router.get("/clicks/summary")
def click_summary(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, list[dict[str, object]]]:
    return {"items": DealsRepository().click_summary(limit=limit)}


@router.get("/deals/{deal_id}", response_model=DealResponse, response_model_by_alias=True)
def get_deal(deal_id: str, currency: str = "USD") -> DealResponse:
    try:
        return deals_service.get_deal(deal_id, currency=currency)
    except DealNotFoundError:
        raise HTTPException(status_code=404, detail="Deal not found") from None


@router.get("/categories")
def categories() -> dict[str, list[str]]:
    return {"items": deals_service.get_categories()}


@router.get("/marketplaces")
def marketplaces() -> dict[str, list[str]]:
    return {"items": deals_service.get_marketplaces()}
