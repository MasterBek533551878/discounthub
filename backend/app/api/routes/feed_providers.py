from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import require_admin_token
from app.models.feed_provider import (
    FeedProviderListResponse,
    FeedProviderResponse,
    FeedProviderSyncResponse,
    FeedSyncRunListResponse,
    FeedProviderUpsertRequest,
)
from app.services.feed_providers_service import FeedProviderNotFoundError, feed_providers_service
from app.repositories.feed_sync_runs_repository import feed_sync_runs_repository
from app.services.feed_sync_scheduler import feed_sync_scheduler

router = APIRouter(
    prefix="/admin/feed-providers",
    tags=["admin-feed-providers"],
    dependencies=[Depends(require_admin_token)],
)


@router.get("", response_model=FeedProviderListResponse, response_model_by_alias=True)
def admin_list_feed_providers(enabled_only: bool = False) -> FeedProviderListResponse:
    items = feed_providers_service.list_providers(enabled_only=enabled_only)
    return FeedProviderListResponse(items=items, total=len(items))


@router.post("", response_model=FeedProviderResponse, response_model_by_alias=True)
def admin_upsert_feed_provider(payload: FeedProviderUpsertRequest) -> FeedProviderResponse:
    return feed_providers_service.upsert_provider(payload)


@router.post("/sync-all", response_model=FeedProviderSyncResponse, response_model_by_alias=True)
def admin_sync_all_feed_providers(
    timeout_seconds: Annotated[int, Query(ge=3, le=300)] = 20,
) -> FeedProviderSyncResponse:
    return feed_providers_service.sync_all_enabled(timeout_seconds=timeout_seconds)


@router.get("/scheduler/status")
def admin_feed_sync_scheduler_status() -> dict[str, object]:
    return feed_sync_scheduler.status()


@router.post("/scheduler/start")
async def admin_start_feed_sync_scheduler(
    interval_seconds: Annotated[int | None, Query(ge=60, le=86400)] = None,
    timeout_seconds: Annotated[int | None, Query(ge=3, le=300)] = None,
    run_on_startup: bool | None = None,
) -> dict[str, object]:
    await feed_sync_scheduler.start(
        interval_seconds=interval_seconds,
        timeout_seconds=timeout_seconds,
        run_on_startup=run_on_startup,
    )
    return feed_sync_scheduler.status()


@router.post("/scheduler/stop")
async def admin_stop_feed_sync_scheduler() -> dict[str, object]:
    await feed_sync_scheduler.stop()
    return feed_sync_scheduler.status()


@router.post("/scheduler/run-once")
async def admin_run_feed_sync_scheduler_once(
    timeout_seconds: Annotated[int | None, Query(ge=3, le=300)] = None,
) -> dict[str, object]:
    return await feed_sync_scheduler.run_once(timeout_seconds=timeout_seconds)




@router.get("/sync-runs", response_model=FeedSyncRunListResponse, response_model_by_alias=True)
def admin_list_feed_sync_runs(
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    provider_id: str | None = None,
    status: str | None = None,
) -> FeedSyncRunListResponse:
    items = feed_sync_runs_repository.list_runs(
        limit=limit,
        provider_id=provider_id,
        status=status,
    )
    return FeedSyncRunListResponse(items=items, total=feed_sync_runs_repository.count_runs())


@router.delete("/sync-runs")
def admin_clear_feed_sync_runs() -> dict[str, object]:
    deleted = feed_sync_runs_repository.clear_runs()
    return {
        "status": "ok",
        "message": f"Deleted {deleted} sync log item(s).",
        "deletedCount": deleted,
    }

@router.get("/{provider_id}", response_model=FeedProviderResponse, response_model_by_alias=True)
def admin_get_feed_provider(provider_id: str) -> FeedProviderResponse:
    try:
        return feed_providers_service.get_provider(provider_id)
    except FeedProviderNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feed provider not found") from None


@router.post("/{provider_id}/sync", response_model=FeedProviderSyncResponse, response_model_by_alias=True)
def admin_sync_feed_provider(
    provider_id: str,
    timeout_seconds: Annotated[int, Query(ge=3, le=300)] = 20,
) -> FeedProviderSyncResponse:
    try:
        return feed_providers_service.sync_provider(provider_id, timeout_seconds=timeout_seconds)
    except FeedProviderNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feed provider not found") from None


@router.delete("/{provider_id}", response_model=FeedProviderSyncResponse, response_model_by_alias=True)
def admin_delete_feed_provider(provider_id: str) -> FeedProviderSyncResponse:
    deleted = feed_providers_service.delete_provider(provider_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feed provider not found")
    return FeedProviderSyncResponse(
        status="ok",
        message=f"Deleted feed provider {provider_id}.",
        provider_id=provider_id,
        imported_count=0,
    )
