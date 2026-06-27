from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from app.models.partner_offer import (
    PartnerOfferResponse,
    PartnerOffersPage,
    PartnerOfferSort,
)
from app.repositories.partner_offers_repository import PartnerOffersRepository
from app.services.partner_offers_service import (
    PartnerOfferNotFoundError,
    partner_offers_service,
)

router = APIRouter(tags=["partner-offers"])


def _safe_offer_target(offer: PartnerOfferResponse) -> str | None:
    checkout_url = (offer.checkout_url or "").strip()
    landing_url = (offer.landing_url or "").strip()
    return checkout_url or landing_url or None


@router.get("/partner-offers", response_model=PartnerOffersPage, response_model_by_alias=True)
def list_partner_offers(
    q: str | None = None,
    category: str | None = None,
    sort: PartnerOfferSort = "featured",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PartnerOffersPage:
    items, total = partner_offers_service.list_offers(
        q=q,
        category=category,
        sort=sort,
        page=page,
        page_size=page_size,
    )

    return PartnerOffersPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next_page=page * page_size < total,
    )


@router.get("/partner-offers/categories")
def partner_offer_categories(q: str | None = None) -> dict[str, list[dict[str, object]]]:
    return {"items": partner_offers_service.get_category_facets(q=q)}


@router.get("/partner-offers/{offer_id}", response_model=PartnerOfferResponse, response_model_by_alias=True)
def get_partner_offer(offer_id: str) -> PartnerOfferResponse:
    try:
        return partner_offers_service.get_offer(offer_id)
    except PartnerOfferNotFoundError:
        raise HTTPException(status_code=404, detail="Partner offer not found") from None


@router.get("/partner-offers/{offer_id}/click", include_in_schema=True)
def click_partner_offer(offer_id: str, request: Request) -> RedirectResponse:
    try:
        offer = partner_offers_service.get_offer(offer_id)
    except PartnerOfferNotFoundError:
        raise HTTPException(status_code=404, detail="Partner offer not found") from None

    target_url = _safe_offer_target(offer)
    if not target_url:
        raise HTTPException(status_code=404, detail="Partner offer link not available")

    PartnerOffersRepository().record_click(
        offer_id=offer.id,
        partner_name=offer.partner_name,
        category=offer.category,
        monetization_mode=offer.monetization_mode,
        target_url=target_url,
        referrer=request.headers.get("referer"),
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
        clicked_at=datetime.now(timezone.utc),
    )

    return RedirectResponse(url=target_url, status_code=302)
