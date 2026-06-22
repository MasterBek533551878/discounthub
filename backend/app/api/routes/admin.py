from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import require_admin_token
from app.models.deal import (
    AdminActionResponse,
    BulkDealUpsertRequest,
    DealMonetizationMode,
    DealResponse,
    DealsExportResponse,
    DealsImportRequest,
    DealsImportUrlRequest,
    DealsPage,
    DealSort,
    DealUpsertRequest,
)
from app.models.promotion import (
    AwinPromotionSyncRequest,
    AwinPromotionSyncResponse,
    PromotionCleanupResponse,
)
from app.services.awin_offers_service import awin_offers_service
from app.services.deals_service import DealNotFoundError, deals_service
from app.services.feed_import_service import feed_import_service
from app.services.promotions_service import promotions_service
from app.services.promotion_cleanup_service import promotion_cleanup_service

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin_token)],
)


@router.post(
    "/promotions/awin/sync",
    response_model=AwinPromotionSyncResponse,
    response_model_by_alias=True,
)
def admin_sync_awin_promotions(payload: AwinPromotionSyncRequest) -> AwinPromotionSyncResponse:
    total_before = promotions_service.count_promotions()
    promotions, skipped_count, pages_checked = awin_offers_service.fetch_promotions(payload)
    imported_count = promotions_service.upsert_promotions(promotions)
    cleanup_result = promotion_cleanup_service.cleanup_promotions()
    total_after = cleanup_result.remaining_count

    return AwinPromotionSyncResponse(
        status="ok",
        message=(
            f"Imported/updated {imported_count} Awin promotion(s). "
            f"Cleaned {cleanup_result.deleted_count} expired/low-value promotion(s)."
        ),
        fetched_count=len(promotions) + skipped_count,
        imported_count=imported_count,
        total_before=total_before,
        total_after=total_after,
        skipped_count=skipped_count,
        pages_checked=pages_checked,
        cleanup_deleted_count=cleanup_result.deleted_count,
        cleanup_deleted_reasons=cleanup_result.deleted_reasons,
    )


@router.post(
    "/promotions/cleanup",
    response_model=PromotionCleanupResponse,
    response_model_by_alias=True,
)
def admin_cleanup_promotions() -> PromotionCleanupResponse:
    result = promotion_cleanup_service.cleanup_promotions()
    return PromotionCleanupResponse(
        status="ok",
        message=f"Cleaned {result.deleted_count} expired/low-value promotion(s).",
        checked_count=result.checked_count,
        deleted_count=result.deleted_count,
        remaining_count=result.remaining_count,
        deleted_reasons=result.deleted_reasons,
    )


@router.get("/deals", response_model=DealsPage, response_model_by_alias=True)
def admin_list_deals(
    q: str | None = None,
    platform: str | None = None,
    category: str | None = None,
    ships_to: str | None = None,
    currency: str = "USD",
    monetization_mode: DealMonetizationMode | None = None,
    sort: DealSort = "newest",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 100,
) -> DealsPage:
    items, total = deals_service.list_deals(
        q=q,
        platform=platform,
        category=category,
        ships_to=ships_to,
        currency=currency,
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


@router.post("/deals", response_model=DealResponse, response_model_by_alias=True)
def admin_upsert_deal(payload: DealUpsertRequest, currency: str = "USD") -> DealResponse:
    return deals_service.upsert_deal(payload, currency=currency)


@router.post("/deals/bulk", response_model=AdminActionResponse, response_model_by_alias=True)
def admin_upsert_deals(payload: BulkDealUpsertRequest) -> AdminActionResponse:
    count = deals_service.upsert_deals(payload.items)
    return AdminActionResponse(
        status="ok",
        message=f"Upserted {count} deal(s).",
        deal_count=deals_service.count_deals(),
    )


@router.get("/deals/export", response_model=DealsExportResponse, response_model_by_alias=True)
def admin_export_deals() -> DealsExportResponse:
    items = deals_service.export_deals()
    return DealsExportResponse(
        status="ok",
        exported_at=datetime.now(timezone.utc),
        total=len(items),
        items=items,
    )


@router.post("/deals/import", response_model=AdminActionResponse, response_model_by_alias=True)
def admin_import_deals(payload: DealsImportRequest) -> AdminActionResponse:
    count = deals_service.import_deals(payload.items, replace=payload.replace)
    mode = "replaced database with" if payload.replace else "imported/updated"
    return AdminActionResponse(
        status="ok",
        message=f"Successfully {mode} {count} deal(s).",
        deal_count=deals_service.count_deals(),
    )


@router.post("/deals/import-url", response_model=AdminActionResponse, response_model_by_alias=True)
def admin_import_deals_from_url(payload: DealsImportUrlRequest) -> AdminActionResponse:
    import_request = feed_import_service.build_import_request_from_url(
        url=payload.url,
        adapter=payload.adapter,
        replace=payload.replace,
        timeout_seconds=payload.timeout_seconds,
    )
    count = deals_service.import_deals(import_request.items, replace=import_request.replace)
    mode = "replaced database with" if import_request.replace else "imported/updated"
    return AdminActionResponse(
        status="ok",
        message=f"Successfully {mode} {count} deal(s) from URL.",
        deal_count=deals_service.count_deals(),
    )


@router.delete("/deals/{deal_id}", response_model=AdminActionResponse, response_model_by_alias=True)
def admin_delete_deal(deal_id: str) -> AdminActionResponse:
    deleted = deals_service.delete_deal(deal_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")

    return AdminActionResponse(
        status="ok",
        message=f"Deleted deal {deal_id}.",
        deal_count=deals_service.count_deals(),
    )


@router.post("/deals/reset-demo", response_model=AdminActionResponse, response_model_by_alias=True)
def admin_reset_demo_deals() -> AdminActionResponse:
    count = deals_service.reset_demo_deals()
    return AdminActionResponse(
        status="ok",
        message="Database reset to demo deals.",
        deal_count=count,
    )


@router.get("/deals/{deal_id}", response_model=DealResponse, response_model_by_alias=True)
def admin_get_deal(deal_id: str, currency: str = "USD") -> DealResponse:
    try:
        return deals_service.get_deal(deal_id, currency=currency)
    except DealNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found") from None
