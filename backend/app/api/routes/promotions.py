from datetime import datetime, timezone
from typing import Annotated
import urllib.parse

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from app.models.promotion import (
    PromotionCountriesResponse,
    PromotionsPage,
    PromotionResponse,
    PromotionSort,
    PromotionType,
)
from app.core.config import get_settings
from app.repositories.promotions_repository import PromotionsRepository
from app.services.promotions_service import PromotionNotFoundError, promotions_service

router = APIRouter(tags=["promotions"])


def _safe_promotion_target(promotion: PromotionResponse) -> str | None:
    affiliate_url = (promotion.affiliate_url or "").strip()
    landing_url = (promotion.landing_url or "").strip()

    repaired = _repair_awin_promotion_target(
        affiliate_url=affiliate_url,
        landing_url=landing_url,
        provider_id=promotion.provider_id,
    )
    return repaired or affiliate_url or landing_url or None


def _repair_awin_promotion_target(
    *,
    affiliate_url: str | None,
    landing_url: str | None,
    provider_id: str | None,
) -> str | None:
    """Keep old Awin promotion rows clickable even when urlTracking is weak.

    Awin Offers rows sometimes arrive with a direct promotion URL only, or with
    an Awin tracking URL whose destination is missing/empty. In those cases we
    can safely rebuild a normal cread.php link from provider_id + publisher id +
    landing_url. Existing good tracking URLs are left unchanged.
    """
    landing = (landing_url or "").strip()
    raw_affiliate = (affiliate_url or "").strip()

    advertiser_id = _awin_advertiser_id(provider_id)
    publisher_id = get_settings().awin_publisher_id.strip()

    if raw_affiliate:
        parsed = urllib.parse.urlparse(raw_affiliate)
        host = parsed.netloc.lower()
        if "awin1.com" not in host:
            return raw_affiliate

        pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        params = dict(pairs)
        existing_ued = (params.get("ued") or "").strip()
        if existing_ued and not _looks_like_generic_store_url(existing_ued):
            return raw_affiliate

        if not landing:
            return raw_affiliate

        params["ued"] = landing
        if advertiser_id and not params.get("awinmid"):
            params["awinmid"] = advertiser_id
        if publisher_id and not params.get("awinaffid"):
            params["awinaffid"] = publisher_id

        return urllib.parse.urlunparse(
            parsed._replace(query=urllib.parse.urlencode(params, doseq=True))
        )

    if advertiser_id and publisher_id and landing:
        query = urllib.parse.urlencode(
            {
                "awinmid": advertiser_id,
                "awinaffid": publisher_id,
                "ued": landing,
            }
        )
        return f"https://www.awin1.com/cread.php?{query}"

    return None


def _awin_advertiser_id(provider_id: str | None) -> str | None:
    raw = str(provider_id or "").strip()
    prefix = "awin_offers_"
    if not raw.startswith(prefix):
        return None
    value = raw.removeprefix(prefix).strip()
    return value if value.isdigit() else None


def _looks_like_generic_store_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(urllib.parse.unquote(url))
    host = parsed.netloc.lower()
    path = parsed.path.strip("/").lower()
    if not host:
        return True
    return path in {"", "/"} and any(
        domain in host for domain in ("alibaba.com", "aliexpress.com")
    )


@router.get("/promotions", response_model=PromotionsPage, response_model_by_alias=True)
def list_promotions(
    q: str | None = None,
    type: PromotionType | None = None,
    store: str | None = None,
    country: str | None = None,
    sort: PromotionSort = "featured",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PromotionsPage:
    items, total = promotions_service.list_promotions(
        q=q,
        type=type,
        store=store,
        country=country,
        sort=sort,
        page=page,
        page_size=page_size,
    )

    return PromotionsPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next_page=page * page_size < total,
    )


@router.get("/promotions/stores")
def promotion_stores(
    q: str | None = None,
    type: PromotionType | None = None,
) -> dict[str, list[dict[str, object]]]:
    return {"items": promotions_service.get_store_facets(q=q, type=type)}


@router.get(
    "/promotions/countries",
    response_model=PromotionCountriesResponse,
    response_model_by_alias=True,
)
def promotion_countries(
    q: str | None = None,
    type: PromotionType | None = None,
    store: str | None = None,
) -> PromotionCountriesResponse:
    return promotions_service.get_country_facets(q=q, type=type, store=store)


@router.get("/promotions/{promotion_id}", response_model=PromotionResponse, response_model_by_alias=True)
def get_promotion(promotion_id: str) -> PromotionResponse:
    try:
        return promotions_service.get_promotion(promotion_id)
    except PromotionNotFoundError:
        raise HTTPException(status_code=404, detail="Promotion not found") from None


@router.get("/promotions/{promotion_id}/click", include_in_schema=True)
def click_promotion(promotion_id: str, request: Request) -> RedirectResponse:
    try:
        promotion = promotions_service.get_promotion(promotion_id)
    except PromotionNotFoundError:
        raise HTTPException(status_code=404, detail="Promotion not found") from None

    target_url = _safe_promotion_target(promotion)
    if not target_url:
        raise HTTPException(status_code=404, detail="Promotion link not available")

    PromotionsRepository().record_click(
        promotion_id=promotion.id,
        store=promotion.store,
        type=promotion.type,
        provider_id=promotion.provider_id,
        monetization_mode=promotion.monetization_mode,
        target_url=target_url,
        referrer=request.headers.get("referer"),
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
        clicked_at=datetime.now(timezone.utc),
    )

    return RedirectResponse(url=target_url, status_code=302)
