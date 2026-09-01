from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from app.core.config import get_settings
from app.models.promotion import AwinPromotionSyncRequest
from app.services.awin_offers_service import awin_offers_service
from app.services.feed_providers_service import feed_providers_service
from app.services.promotion_cleanup_service import promotion_cleanup_service
from app.services.promotions_service import promotions_service


class FeedSyncScheduler:
    """Runs the production data maintenance loop.

    This scheduler used to refresh only product feed providers. DiscountHub also
    needs store-level Awin promotions and cleanup to be automatic, otherwise the
    app can show stale coupons or miss newly joined stores until somebody runs a
    manual script. A single run now refreshes products, refreshes Awin offers,
    and cleans expired/low-value promotions.
    """

    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()
        self._interval_seconds = 3600
        self._timeout_seconds = 20
        self._run_on_startup = False
        self._started_at: datetime | None = None
        self._last_run_at: datetime | None = None
        self._last_finished_at: datetime | None = None
        self._last_status: str | None = None
        self._last_message: str | None = None
        self._last_imported_count = 0
        self._last_deal_count: int | None = None
        self._last_promotion_imported_count = 0
        self._last_promotion_cleanup_deleted_count = 0
        self._last_promotion_count: int | None = None
        self._last_promotion_error: str | None = None
        self._last_error: str | None = None

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(
        self,
        *,
        interval_seconds: int | None = None,
        timeout_seconds: int | None = None,
        run_on_startup: bool | None = None,
    ) -> None:
        if self.is_running:
            return

        settings = get_settings()
        self._interval_seconds = max(60, int(interval_seconds or settings.feed_sync_interval_seconds))
        self._timeout_seconds = max(3, int(timeout_seconds or settings.feed_sync_timeout_seconds))
        self._run_on_startup = settings.feed_sync_run_on_startup if run_on_startup is None else run_on_startup
        self._started_at = datetime.now(timezone.utc)
        self._task = asyncio.create_task(self._run_loop(), name="feed-sync-scheduler")

    async def stop(self) -> None:
        if self._task is None:
            return

        task = self._task
        self._task = None
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def run_once(self, *, timeout_seconds: int | None = None) -> dict[str, Any]:
        if self._lock.locked():
            return {
                "status": "busy",
                "message": "DiscountHub data maintenance is already running.",
                "importedCount": 0,
                "dealCount": self._last_deal_count,
                "promotionImportedCount": 0,
                "promotionCount": self._last_promotion_count,
            }

        async with self._lock:
            started_at = datetime.now(timezone.utc)
            self._last_run_at = started_at
            timeout = max(3, int(timeout_seconds or self._timeout_seconds))

            try:
                result = await asyncio.to_thread(self._run_maintenance_once, timeout)
                finished_at = datetime.now(timezone.utc)
                self._last_finished_at = finished_at
                self._last_status = str(result["status"])
                self._last_message = str(result["message"])
                self._last_imported_count = int(result.get("importedCount") or 0)
                self._last_deal_count = self._safe_int(result.get("dealCount"))
                self._last_promotion_imported_count = int(result.get("promotionImportedCount") or 0)
                self._last_promotion_cleanup_deleted_count = int(result.get("promotionCleanupDeletedCount") or 0)
                self._last_promotion_count = self._safe_int(result.get("promotionCount"))
                self._last_promotion_error = result.get("promotionError") if result.get("promotionError") else None
                self._last_error = None if self._last_status != "error" else self._last_message

                result["startedAt"] = started_at.isoformat()
                result["finishedAt"] = finished_at.isoformat()
                return result
            except Exception as exc:  # pragma: no cover - defensive runtime guard
                finished_at = datetime.now(timezone.utc)
                message = f"Scheduled data maintenance failed: {self._exception_message(exc)}"
                self._last_finished_at = finished_at
                self._last_status = "error"
                self._last_message = message
                self._last_imported_count = 0
                self._last_error = message

                return {
                    "status": "error",
                    "message": message,
                    "importedCount": 0,
                    "dealCount": self._last_deal_count,
                    "promotionImportedCount": 0,
                    "promotionCleanupDeletedCount": 0,
                    "promotionCount": self._last_promotion_count,
                    "startedAt": started_at.isoformat(),
                    "finishedAt": finished_at.isoformat(),
                }

    def _run_maintenance_once(self, timeout_seconds: int) -> dict[str, Any]:
        settings = get_settings()
        product_result = feed_providers_service.sync_all_enabled(timeout_seconds=timeout_seconds)

        promotion_status = "skipped"
        promotion_error: str | None = None
        promotion_imported_count = 0
        stale_deleted_count = 0
        promotion_fetched_count = 0
        promotion_skipped_count = 0
        promotion_pages_checked = 0

        if settings.awin_promotions_auto_sync_enabled:
            try:
                request = AwinPromotionSyncRequest(
                    page_size=settings.awin_promotions_sync_page_size,
                    max_pages=settings.awin_promotions_sync_max_pages,
                )
                (
                    promotions,
                    skipped_count,
                    pages_checked,
                    seen_promotion_ids,
                    snapshot_complete,
                ) = awin_offers_service.fetch_promotions(request)
                promotion_imported_count = promotions_service.upsert_promotions(promotions)
                promotion_fetched_count = len(promotions) + skipped_count
                promotion_skipped_count = skipped_count
                promotion_pages_checked = pages_checked

                # Pruning must use every raw promotion ID returned by Awin,
                # not only offers that passed DiscountHub filtering.
                #
                # This distinguishes:
                #   "Awin no longer has this offer"
                # from
                #   "DiscountHub decided not to display this offer".
                #
                # Fail-safe: an incomplete or unexpectedly empty snapshot never
                # receives permission to delete stored Awin promotions.
                snapshot_safe_to_prune = (
                    snapshot_complete
                    and bool(seen_promotion_ids)
                )

                if snapshot_safe_to_prune:
                    stale_deleted_count = promotions_service.delete_missing_awin_promotions(
                        seen_promotion_ids
                    )
                else:
                    stale_deleted_count = 0

                promotion_status = "ok"
            except Exception as exc:  # Keep products alive even if Awin offers fails.
                promotion_status = "error"
                promotion_error = self._exception_message(exc)

        cleanup_result = promotion_cleanup_service.cleanup_promotions()
        promotion_count = cleanup_result.remaining_count

        status = "ok"
        if product_result.status != "ok" or promotion_status == "error" or cleanup_result.error:
            status = "partial"
        if product_result.status == "error":
            status = "error"

        message_parts = [product_result.message]
        if promotion_status == "ok":
            message_parts.append(
                f"Awin promotions imported/updated {promotion_imported_count}; "
                f"removed {stale_deleted_count} stale Awin promotion(s); "
                f"cleaned {cleanup_result.deleted_count}."
            )
        elif promotion_status == "skipped":
            message_parts.append(f"Awin promotion auto-sync disabled; cleaned {cleanup_result.deleted_count}.")
        else:
            message_parts.append(
                f"Awin promotion sync failed: {promotion_error}. "
                f"Cleanup still removed {cleanup_result.deleted_count}."
            )

        return {
            "status": status,
            "message": " ".join(part for part in message_parts if part),
            "importedCount": product_result.imported_count,
            "dealCount": product_result.deal_count,
            "promotionStatus": promotion_status,
            "promotionImportedCount": promotion_imported_count,
            "promotionFetchedCount": promotion_fetched_count,
            "promotionSkippedCount": promotion_skipped_count,
            "promotionPagesChecked": promotion_pages_checked,
            "promotionStaleDeletedCount": stale_deleted_count,
            "promotionCleanupDeletedCount": cleanup_result.deleted_count,
            "promotionCleanupDeletedReasons": cleanup_result.deleted_reasons,
            "promotionCount": promotion_count,
            "promotionError": promotion_error,
        }

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.is_running,
            "intervalSeconds": self._interval_seconds,
            "timeoutSeconds": self._timeout_seconds,
            "runOnStartup": self._run_on_startup,
            "startedAt": self._started_at.isoformat() if self._started_at else None,
            "lastRunAt": self._last_run_at.isoformat() if self._last_run_at else None,
            "lastFinishedAt": self._last_finished_at.isoformat() if self._last_finished_at else None,
            "lastStatus": self._last_status,
            "lastMessage": self._last_message,
            "lastImportedCount": self._last_imported_count,
            "lastDealCount": self._last_deal_count,
            "lastPromotionImportedCount": self._last_promotion_imported_count,
            "lastPromotionCleanupDeletedCount": self._last_promotion_cleanup_deleted_count,
            "lastPromotionCount": self._last_promotion_count,
            "lastPromotionError": self._last_promotion_error,
            "lastError": self._last_error,
        }

    async def _run_loop(self) -> None:
        if self._run_on_startup:
            await self.run_once()

        while True:
            await asyncio.sleep(self._interval_seconds)
            await self.run_once()

    @staticmethod
    def _exception_message(exc: Exception) -> str:
        detail = getattr(exc, "detail", None)
        if detail:
            return str(detail)
        return str(exc) or exc.__class__.__name__

    @staticmethod
    def _safe_int(value: object) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None


feed_sync_scheduler = FeedSyncScheduler()
