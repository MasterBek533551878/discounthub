from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from app.models.promotion import (
    PromotionsPage,
    PromotionResponse,
    PromotionSort,
    PromotionType,
)
from app.repositories.promotions_repository import PromotionsRepository
from app.services.promotions_service import PromotionNotFoundError, promotions_service

router = APIRouter(tags=["promotions"])


def _safe_promotion_target(promotion: PromotionResponse) -> str | None:
    affiliate_url = (promotion.affiliate_url or "").strip()
    landing_url = (promotion.landing_url or "").strip()
    return affiliate_url or landing_url or None


@router.get("/promotions", response_model=PromotionsPage, response_model_by_alias=True)
def list_promotions(
    q: str | None = None,
    type: PromotionType | None = None,
    store: str | None = None,
    sort: PromotionSort = "featured",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PromotionsPage:
    items, total = promotions_service.list_promotions(
        q=q,
        type=type,
        store=store,
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
