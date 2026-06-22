from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status

from app.models.feed_provider import (
    FeedProvider,
    FeedProviderResponse,
    FeedProviderSyncResponse,
    FeedProviderUpsertRequest,
)
from app.repositories.feed_providers_repository import FeedProvidersRepository
from app.repositories.feed_sync_runs_repository import feed_sync_runs_repository
from app.services.deals_service import deals_service
from app.services.feed_import_service import feed_import_service


class FeedProviderNotFoundError(Exception):
    pass


class FeedProvidersService:
    def __init__(self, repository: FeedProvidersRepository | None = None) -> None:
        self._repository = repository or FeedProvidersRepository()

    def list_providers(self, *, enabled_only: bool = False) -> list[FeedProviderResponse]:
        return [self._to_response(provider) for provider in self._repository.list_providers(enabled_only=enabled_only)]

    def get_provider(self, provider_id: str) -> FeedProviderResponse:
        provider = self._repository.get_provider(provider_id)
        if provider is None:
            raise FeedProviderNotFoundError(provider_id)
        return self._to_response(provider)

    def upsert_provider(self, payload: FeedProviderUpsertRequest) -> FeedProviderResponse:
        now = datetime.now(timezone.utc)
        existing = self._repository.get_provider(payload.id.strip())

        provider = FeedProvider(
            id=payload.id.strip(),
            name=payload.name.strip(),
            url=payload.url.strip(),
            adapter=payload.adapter,
            enabled=payload.enabled,
            replace_on_sync=payload.replace_on_sync,
            monetization_mode=payload.monetization_mode,
            last_sync_at=existing.last_sync_at if existing else None,
            last_status=existing.last_status if existing else None,
            last_message=existing.last_message if existing else None,
            last_imported_count=existing.last_imported_count if existing else 0,
            created_at=existing.created_at if existing else now,
            updated_at=now,
        )
        self._repository.upsert_provider(provider)
        return self._to_response(provider)

    def delete_provider(self, provider_id: str) -> bool:
        return self._repository.delete_provider(provider_id)

    def sync_provider(self, provider_id: str, *, timeout_seconds: int = 20) -> FeedProviderSyncResponse:
        provider = self._repository.get_provider(provider_id)
        if provider is None:
            raise FeedProviderNotFoundError(provider_id)

        return self._sync_provider(provider, timeout_seconds=timeout_seconds)

    def sync_all_enabled(self, *, timeout_seconds: int = 20) -> FeedProviderSyncResponse:
        providers = self._repository.list_providers(enabled_only=True)
        if not providers:
            return FeedProviderSyncResponse(
                status="ok",
                message="No enabled feed providers to sync.",
                imported_count=0,
                deal_count=deals_service.count_deals(),
            )

        imported_total = 0
        failures: list[str] = []
        for provider in providers:
            try:
                result = self._sync_provider(provider, timeout_seconds=timeout_seconds)
                imported_total += result.imported_count
            except HTTPException as exc:
                failures.append(f"{provider.id}: {exc.detail}")

        if failures:
            return FeedProviderSyncResponse(
                status="partial",
                message=f"Synced with {len(failures)} failure(s): " + "; ".join(failures[:3]),
                imported_count=imported_total,
                deal_count=deals_service.count_deals(),
            )

        return FeedProviderSyncResponse(
            status="ok",
            message=f"Synced {len(providers)} provider(s).",
            imported_count=imported_total,
            deal_count=deals_service.count_deals(),
        )

    def _sync_provider(self, provider: FeedProvider, *, timeout_seconds: int) -> FeedProviderSyncResponse:
        synced_at = datetime.now(timezone.utc)
        try:
            import_request = feed_import_service.build_import_request_from_url(
                url=provider.url,
                adapter=provider.adapter,
                replace=provider.replace_on_sync,
                timeout_seconds=timeout_seconds,
            )
            for item in import_request.items:
                if not item.provider_id:
                    item.provider_id = provider.id
                if item.monetization_mode is None:
                    affiliate_url = str(item.affiliate_url or "").strip()
                    product_url = str(item.product_url or "").strip()
                    if provider.monetization_mode != "direct":
                        item.monetization_mode = provider.monetization_mode
                    elif affiliate_url and affiliate_url != product_url:
                        item.monetization_mode = "affiliate"
                    else:
                        item.monetization_mode = "direct"
            imported_count = deals_service.import_deals(
                import_request.items,
                replace=import_request.replace,
            )
            stale_deleted_count = 0
            if not import_request.replace:
                # Incremental affiliate feeds do not always send tombstones for
                # products that disappeared from the merchant catalogue. After a
                # successful sync, remove very old rows for the same provider so
                # dead products cannot accumulate forever. Public visibility is
                # still controlled separately by the freshness SQL window.
                stale_deleted_count = deals_service.delete_stale_provider_deals(
                    provider_id=provider.id,
                    older_than=synced_at - timedelta(days=10),
                )
            deal_count = deals_service.count_deals()
            finished_at = datetime.now(timezone.utc)
            message = f"Successfully synced {imported_count} deal(s)."
            if stale_deleted_count:
                message += f" Removed {stale_deleted_count} stale provider deal(s)."
            self._repository.update_sync_result(
                provider.id,
                status="ok",
                message=message,
                imported_count=imported_count,
                synced_at=synced_at,
            )
            feed_sync_runs_repository.add_run(
                provider_id=provider.id,
                provider_name=provider.name,
                url=provider.url,
                status="ok",
                message=message,
                imported_count=imported_count,
                deal_count=deal_count,
                started_at=synced_at,
                finished_at=finished_at,
            )
            return FeedProviderSyncResponse(
                status="ok",
                message=message,
                provider_id=provider.id,
                imported_count=imported_count,
                deal_count=deal_count,
            )
        except HTTPException as exc:
            finished_at = datetime.now(timezone.utc)
            message = str(exc.detail)
            deal_count = deals_service.count_deals()
            self._repository.update_sync_result(
                provider.id,
                status="error",
                message=message,
                imported_count=0,
                synced_at=synced_at,
            )
            feed_sync_runs_repository.add_run(
                provider_id=provider.id,
                provider_name=provider.name,
                url=provider.url,
                status="error",
                message=message,
                imported_count=0,
                deal_count=deal_count,
                started_at=synced_at,
                finished_at=finished_at,
            )
            raise
        except Exception as exc:
            finished_at = datetime.now(timezone.utc)
            message = f"Unexpected feed sync error: {exc}"
            deal_count = deals_service.count_deals()
            self._repository.update_sync_result(
                provider.id,
                status="error",
                message=message,
                imported_count=0,
                synced_at=synced_at,
            )
            feed_sync_runs_repository.add_run(
                provider_id=provider.id,
                provider_name=provider.name,
                url=provider.url,
                status="error",
                message=message,
                imported_count=0,
                deal_count=deal_count,
                started_at=synced_at,
                finished_at=finished_at,
            )
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc

    def _to_response(self, provider: FeedProvider) -> FeedProviderResponse:
        return FeedProviderResponse(
            id=provider.id,
            name=provider.name,
            url=provider.url,
            adapter=provider.adapter,
            enabled=provider.enabled,
            replace_on_sync=provider.replace_on_sync,
            monetization_mode=provider.monetization_mode,
            last_sync_at=provider.last_sync_at,
            last_status=provider.last_status,
            last_message=provider.last_message,
            last_imported_count=provider.last_imported_count,
            created_at=provider.created_at,
            updated_at=provider.updated_at,
        )


feed_providers_service = FeedProvidersService()
