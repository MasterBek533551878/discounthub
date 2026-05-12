from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from app.models.deal import DealsPage, DealResponse, DealSort
from app.repositories.deals_repository import DealsRepository
from app.services.deals_service import DealNotFoundError, deals_service

router = APIRouter(tags=["deals"])


@router.get("/deals", response_model=DealsPage, response_model_by_alias=True)
def list_deals(
    q: str | None = None,
    platform: str | None = None,
    category: str | None = None,
    ships_to: str | None = None,
    currency: str = "USD",
    min_discount: Annotated[int | None, Query(ge=0, le=100)] = None,
    min_rating: Annotated[float | None, Query(ge=0, le=5)] = None,
    max_price: Annotated[float | None, Query(gt=0)] = None,
    free_shipping: bool | None = None,
    verified: bool | None = None,
    sort: DealSort = "score_desc",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DealsPage:
    items, total = deals_service.list_deals(
        q=q,
        platform=platform,
        category=category,
        ships_to=ships_to,
        currency=currency,
        min_discount=min_discount,
        min_rating=min_rating,
        max_price=max_price,
        free_shipping=free_shipping,
        verified=verified,
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


@router.get("/deals/{deal_id}/click", include_in_schema=True)
def click_deal(deal_id: str, request: Request) -> RedirectResponse:
    try:
        deal = deals_service.get_deal(deal_id, currency="USD")
    except DealNotFoundError:
        raise HTTPException(status_code=404, detail="Deal not found") from None

    target_url = deal.affiliate_url or deal.product_url
    if not target_url:
        raise HTTPException(status_code=404, detail="Deal link not available")

    repository = DealsRepository()
    repository.record_click(
        deal_id=deal.id,
        platform=deal.platform,
        category=deal.category,
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
