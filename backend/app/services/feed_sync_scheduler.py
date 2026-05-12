from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from app.core.config import get_settings
from app.services.feed_providers_service import feed_providers_service


class FeedSyncScheduler:
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
                "message": "Feed sync is already running.",
                "importedCount": 0,
                "dealCount": self._last_deal_count,
            }

        async with self._lock:
            started_at = datetime.now(timezone.utc)
            self._last_run_at = started_at
            timeout = max(3, int(timeout_seconds or self._timeout_seconds))

            try:
                result = await asyncio.to_thread(
                    feed_providers_service.sync_all_enabled,
                    timeout_seconds=timeout,
                )
                finished_at = datetime.now(timezone.utc)
                self._last_finished_at = finished_at
                self._last_status = result.status
                self._last_message = result.message
                self._last_imported_count = result.imported_count
                self._last_deal_count = result.deal_count
                self._last_error = None

                return {
                    "status": result.status,
                    "message": result.message,
                    "importedCount": result.imported_count,
                    "dealCount": result.deal_count,
                    "startedAt": started_at.isoformat(),
                    "finishedAt": finished_at.isoformat(),
                }
            except Exception as exc:  # pragma: no cover - defensive runtime guard
                finished_at = datetime.now(timezone.utc)
                message = f"Scheduled feed sync failed: {exc}"
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
                    "startedAt": started_at.isoformat(),
                    "finishedAt": finished_at.isoformat(),
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
            "lastError": self._last_error,
        }

    async def _run_loop(self) -> None:
        if self._run_on_startup:
            await self.run_once()

        while True:
            await asyncio.sleep(self._interval_seconds)
            await self.run_once()


feed_sync_scheduler = FeedSyncScheduler()
